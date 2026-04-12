import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from analyzer.audio import analyze_audio
from analyzer.features import analyze_features
from analyzer.retention import compute_retention_analysis
from analyzer.suggestions import generate_suggestions
from analyzer.video import analyze_video
from config import DEMO_MODE
from db import create_job, get_job, init_db, update_job

MAX_CONCURRENT_JOBS = 3
MAX_UPLOAD_BYTES = 500 * 1024 * 1024

_JOB_LOCK = threading.Lock()
_ACTIVE_JOBS = 0
_JOB_START_TIMES = {}
_JOB_END_TIMES = {}
_JOB_PARTIAL_RESULTS = {}


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


def _set_partial_result(job_id: str, data: dict) -> None:
    with _JOB_LOCK:
        _JOB_PARTIAL_RESULTS[job_id] = data


def _finalize_job_tracking(job_id: str) -> None:
    global _ACTIVE_JOBS
    with _JOB_LOCK:
        _ACTIVE_JOBS = max(0, _ACTIVE_JOBS - 1)
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
        _set_partial_result(job_id, {"stage": "analyzing_media"})
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                video_future = executor.submit(analyze_video, video_path, job_id)
                audio_future = executor.submit(analyze_audio, video_path, job_id)
                video_data = video_future.result()
                audio_data = audio_future.result()
        except Exception as exc:
            update_job(
                job_id,
                status="failed",
                progress="Analyzing video and audio...",
                result={"error": str(exc)},
            )
            return

        # Stage 3: features (optional)
        update_job(job_id, progress="Extracting visual features...")
        _set_partial_result(job_id, {"stage": "extracting_features", "video": video_data, "audio": audio_data})
        try:
            features = analyze_features(video_data)
        except Exception:
            features = {"clip_scores": [], "face_data": []}

        # Stage 4: retention (required)
        update_job(job_id, progress="Computing retention curve...")
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
            update_job(
                job_id,
                status="failed",
                progress="Computing retention curve...",
                result={"error": str(exc)},
            )
            return

        # Stage 5: suggestions (fallback handled)
        update_job(job_id, progress="Generating AI suggestions...")
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
        _set_partial_result(job_id, {"stage": "done"})
    finally:
        _finalize_job_tracking(job_id)


@app.get("/health")
def health():
    return {"status": "ok", "message": "backend running"}


@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    global _ACTIVE_JOBS

    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Only video files are allowed")

    with _JOB_LOCK:
        if _ACTIVE_JOBS >= MAX_CONCURRENT_JOBS:
            raise HTTPException(status_code=429, detail="Max 3 concurrent jobs allowed")
        _ACTIVE_JOBS += 1

    job_id = str(uuid4())

    try:
        content = await file.read()
        file_size = len(content)

        if file_size >= MAX_UPLOAD_BYTES:
            with _JOB_LOCK:
                _ACTIVE_JOBS = max(0, _ACTIVE_JOBS - 1)
            raise HTTPException(status_code=400, detail="File must be smaller than 500MB")

        upload_dir = os.path.join("uploads", job_id)
        os.makedirs(upload_dir, exist_ok=True)

        video_path = os.path.join(upload_dir, "video.mp4")
        with open(video_path, "wb") as f:
            f.write(content)

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
            _ACTIVE_JOBS = max(0, _ACTIVE_JOBS - 1)
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")


@app.get("/status/{job_id}")
def get_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    with _JOB_LOCK:
        start_time = _JOB_START_TIMES.get(job_id)
        end_time = _JOB_END_TIMES.get(job_id)
        partial = _JOB_PARTIAL_RESULTS.get(job_id)

    if start_time is None:
        elapsed = 0.0
    elif end_time is not None:
        elapsed = max(0.0, end_time - start_time)
    else:
        elapsed = max(0.0, time.time() - start_time)

    response = {
        "id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "result": job["result"],
        "elapsed_time": round(elapsed, 2),
    }

    if partial is not None:
        response["partial_result"] = partial

    return response
