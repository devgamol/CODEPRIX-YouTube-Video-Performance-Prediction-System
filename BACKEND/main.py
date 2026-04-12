import os
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from analyzer.video import analyze_video
from db import create_job, get_job, init_db, update_job


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


def run_analysis(video_path: str, job_id: str) -> None:
    result = analyze_video(video_path, job_id)
    update_job(job_id, status="completed", result=result)


@app.get("/health")
def health():
    return {"status": "ok", "message": "backend running"}


@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Only video files are allowed")

    job_id = str(uuid4())
    upload_dir = os.path.join("uploads", job_id)
    os.makedirs(upload_dir, exist_ok=True)

    video_path = os.path.join(upload_dir, "video.mp4")
    content = await file.read()
    with open(video_path, "wb") as f:
        f.write(content)

    create_job(job_id)
    background_tasks.add_task(run_analysis, video_path, job_id)

    return {"job_id": job_id, "status": "queued"}


@app.get("/status/{job_id}")
def get_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "result": job["result"],
    }
