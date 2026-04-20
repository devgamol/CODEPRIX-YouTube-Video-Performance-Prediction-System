import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from contextlib import asynccontextmanager
from threading import Lock
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import DuplicateKeyError
from pydantic import BaseModel

from analyzer.audio import analyze_audio
from analyzer.features import analyze_features
from analyzer.retention import compute_retention_analysis
from analyzer.suggestions import generate_suggestions
from analyzer.video import analyze_video
from config import DEMO_MODE
from db import create_job, get_job, init_db, update_job, users_collection
from utils.auth import create_token, decode_token, hash_password, verify_password
from utils.pdf import generate_pdf_bytes

MAX_CONCURRENT_JOBS = 3
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024
ANALYSIS_STAGE_TIMEOUT_SECONDS = 300
active_jobs = 0
lock = Lock()

_JOB_LOCK = threading.Lock()
_JOB_START_TIMES = {}
_JOB_END_TIMES = {}
_JOB_PARTIAL_RESULTS = {}
jobs = {}


class AuthRequest(BaseModel):
    email: str
    password: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No token")

    parts = authorization.split(" ")
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Invalid token")

    token = parts[1]
    try:
        data = decode_token(token)
        return data["email"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def _set_partial_result(job_id: str, data: dict) -> None:
    with _JOB_LOCK:
        _JOB_PARTIAL_RESULTS[job_id] = data


def _finalize_job_tracking(job_id: str) -> None:
    global active_jobs
    with lock:
        active_jobs -= 1
    with _JOB_LOCK:
        _JOB_END_TIMES[job_id] = time.time()


def run_analysis(video_path: str, job_id: str) -> None:
    preprocessing_data = {}
    video_data = {}
    audio_data = {}
    features = {"clip_scores": [], "face_data": []}
    retention_data = {}
    suggestions = []

    try:
        # Stage 1: preprocessing (optional skip)
        update_job(job_id, status="processing", progress="Preprocessing video...")
        with _JOB_LOCK:
            if job_id in jobs:
                jobs[job_id]["progress"] = "Preprocessing video..."
        _set_partial_result(job_id, {"stage": "preprocessing"})
        try:
            if DEMO_MODE:
                preprocessing_data = {"skipped": True}
            else:
                preprocessing_data = {"skipped": False}
        except Exception:
            preprocessing_data = {"skipped": True}

        # Stage 2: parallel analyze_video + analyze_audio
        update_job(job_id, progress="Analyzing video and audio...")
        with _JOB_LOCK:
            if job_id in jobs:
                jobs[job_id]["progress"] = "Analyzing video and audio..."
        _set_partial_result(job_id, {"stage": "analyzing_media"})
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_video = executor.submit(analyze_video, video_path, job_id)
                future_audio = executor.submit(analyze_audio, video_path, job_id)
                video_data = future_video.result()
                audio_data = future_audio.result()
        except FuturesTimeoutError:
            video_data = {}
            audio_data = {}
        except Exception as exc:
            video_data = {}
            audio_data = {"error": str(exc)}

        # Stage 3: features (optional)
        update_job(job_id, progress="Extracting visual features...")
        with _JOB_LOCK:
            if job_id in jobs:
                jobs[job_id]["progress"] = "Extracting visual features..."
        _set_partial_result(job_id, {"stage": "extracting_features", "video": video_data, "audio": audio_data})
        try:
            features = analyze_features(video_data)
        except Exception:
            features = {"clip_scores": [], "face_data": []}

        # Stage 4: retention (required)
        update_job(job_id, progress="Computing retention curve...")
        with _JOB_LOCK:
            if job_id in jobs:
                jobs[job_id]["progress"] = "Computing retention curve..."
        _set_partial_result(
            job_id,
            {
                "stage": "computing_retention",
                "video": video_data,
                "audio": audio_data,
                "features": features,
            },
        )
        try:
            retention_data = compute_retention_analysis(video_data, audio_data, features)
        except Exception as exc:
            retention_data = {"error": str(exc)}

        # Stage 5: suggestions (fallback handled)
        update_job(job_id, progress="Generating AI suggestions...")
        with _JOB_LOCK:
            if job_id in jobs:
                jobs[job_id]["progress"] = "Generating AI suggestions..."
        _set_partial_result(
            job_id,
            {
                "stage": "generating_suggestions",
                "video": video_data,
                "audio": audio_data,
                "features": features,
                "retention": retention_data,
            },
        )
        try:
            suggestions = generate_suggestions(video_data, audio_data, retention_data, features)
        except Exception:
            suggestions = []

        update_job(job_id, progress="Finalizing...")
        with _JOB_LOCK:
            if job_id in jobs:
                jobs[job_id]["progress"] = "Finalizing..."

        result = {
            "preprocessing": preprocessing_data,
            "video": video_data,
            "audio": audio_data,
            "features": features,
            "retention": retention_data,
            "suggestions": suggestions,
        }

        audio_path = os.path.join("uploads", job_id, "audio.wav")
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass

        update_job(job_id, status="done", progress="done", result=result)
        with _JOB_LOCK:
            if job_id in jobs:
                jobs[job_id]["status"] = "done"
                jobs[job_id]["result"] = result
        _set_partial_result(job_id, {"stage": "done"})
    except Exception as exc:
        with _JOB_LOCK:
            if job_id in jobs:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["progress"] = str(exc)
        raise
    finally:
        _finalize_job_tracking(job_id)


@app.get("/health")
def health():
    return {"status": "ok", "message": "backend running"}


@app.post("/signup")
def signup(payload: AuthRequest):
    if users_collection is None:
        raise HTTPException(status_code=500, detail="MongoDB not configured")

    if users_collection.find_one({"email": payload.email}):
        raise HTTPException(status_code=400, detail="User already exists")

    try:
        users_collection.insert_one(
            {
                "email": payload.email,
                "password": hash_password(payload.password),
            }
        )
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="User already exists")

    return {"success": True, "message": "Signup successful"}


@app.post("/login")
def login(payload: AuthRequest):
    if users_collection is None:
        raise HTTPException(status_code=500, detail="MongoDB not configured")

    user = users_collection.find_one({"email": payload.email})
    if not user or not verify_password(payload.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(payload.email)
    return {"token": token}


@app.post("/upload")
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: str = Depends(get_user),
):
    global active_jobs

    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Only video files are allowed")

    original_name = str(file.filename or "video.mp4")
    _, ext = os.path.splitext(original_name)
    ext = ext.lower()
    allowed_exts = {".mp4", ".mov", ".webm", ".mkv"}
    if ext and ext not in allowed_exts:
        raise HTTPException(status_code=400, detail="Unsupported video format. Use MP4, MOV, WEBM, or MKV.")

    with lock:
        if active_jobs >= MAX_CONCURRENT_JOBS:
            raise HTTPException(status_code=429, detail="Server busy, try later")
        active_jobs += 1

    job_id = str(uuid4())
    with _JOB_LOCK:
        jobs[job_id] = {
            "status": "processing",
            "progress": "Starting...",
            "result": None,
        }

    try:
        upload_dir = os.path.join("uploads", job_id)
        os.makedirs(upload_dir, exist_ok=True)

        save_ext = ext if ext else ".mp4"
        video_path = os.path.join(upload_dir, f"video{save_ext}")
        file_size = 0
        with open(video_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > MAX_UPLOAD_BYTES:
                    f.close()
                    try:
                        os.remove(video_path)
                    except Exception:
                        pass
                    with _JOB_LOCK:
                        if job_id in jobs:
                            jobs[job_id]["status"] = "error"
                            jobs[job_id]["progress"] = "File must be smaller than 2GB"
                    with lock:
                        active_jobs -= 1
                    raise HTTPException(status_code=400, detail="File must be smaller than 2GB")
                f.write(chunk)

        create_job(job_id)

        with _JOB_LOCK:
            _JOB_START_TIMES[job_id] = time.time()
            _JOB_PARTIAL_RESULTS[job_id] = {"stage": "queued"}

        size_mb = file_size / (1024 * 1024)
        estimated_processing_time = int(max(15, size_mb * 6))

        background_tasks.add_task(run_analysis, video_path, job_id)

        return {
            "job_id": job_id,
            "estimated_processing_time": estimated_processing_time,
        }
    except HTTPException:
        raise
    except Exception as exc:
        with _JOB_LOCK:
            if job_id in jobs:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["progress"] = str(exc)
        with lock:
            active_jobs -= 1
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")


@app.get("/status/{job_id}")
def get_status(job_id: str, current_user: str = Depends(get_user)):
    with _JOB_LOCK:
        job = jobs.get(job_id)
        start_time = _JOB_START_TIMES.get(job_id)
        end_time = _JOB_END_TIMES.get(job_id)
        partial = _JOB_PARTIAL_RESULTS.get(job_id)
    if job is None:
        db_job = get_job(job_id)
        if db_job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        job = {
            "status": db_job["status"],
            "progress": db_job["progress"],
            "result": db_job["result"],
        }

    if start_time is None:
        elapsed = 0.0
    elif end_time is not None:
        elapsed = max(0.0, end_time - start_time)
    else:
        elapsed = max(0.0, time.time() - start_time)

    response = {
        "id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "result": job["result"],
        "elapsed_time": round(elapsed, 2),
    }

    if partial is not None:
        response["partial_result"] = partial

    return response


@app.post("/export")
def export_pdf(result: dict, current_user: str = Depends(get_user)):
    pdf_bytes = generate_pdf_bytes(result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="report.pdf"'},
    )
