from collections import defaultdict
from pathlib import Path
from threading import Thread
import shutil
import time

import cv2
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from ultralytics import YOLO

app = FastAPI(title="Salamander YOLO Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
MODEL_PATH = BASE_DIR / "models" / "best.pt"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

model = YOLO(str(MODEL_PATH))

job = {
    "status": "idle",
    "percent": 0,
}


@app.get("/")
def home():
    return {"message": "Salamander YOLO FastAPI Backend Running"}


def clean_filename(filename: str) -> str:
    return filename.replace(" ", "_").replace("(", "").replace(")", "")


def run_track_job(input_path: Path, output_path: Path):
    try:
        job.clear()
        job["status"] = "processing"
        job["percent"] = 0

        cap = cv2.VideoCapture(str(input_path))

        if not cap.isOpened():
            raise RuntimeError("Could not open uploaded video.")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0:
            fps = 24

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        frames_seen = defaultdict(int)
        label_for = {}
        total_distance = defaultdict(float)
        previous_center = {}

        frame_metrics = []
        max_simultaneous = 0

        for frame_idx in range(total_frames):
            ok, frame = cap.read()

            if not ok:
                break

            result = model.track(
                frame,
                persist=True,
                conf=0.15,
                verbose=False
            )[0]

            boxes = result.boxes
            detections = []

            if boxes is not None:
                max_simultaneous = max(max_simultaneous, len(boxes))

                ids = boxes.id.tolist() if boxes.id is not None else [None] * len(boxes)
                classes = boxes.cls.tolist() if boxes.cls is not None else [0] * len(boxes)

                for box, track_id, cls_id in zip(boxes, ids, classes):
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2

                    detection = {
                        "trackId": int(track_id) if track_id is not None else None,
                        "label": model.names[int(cls_id)],
                        "centerX": round(center_x, 2),
                        "centerY": round(center_y, 2),
                        "box": [
                            round(x1, 2),
                            round(y1, 2),
                            round(x2, 2),
                            round(y2, 2),
                        ],
                    }

                    detections.append(detection)

                    if track_id is not None:
                        tid = int(track_id)
                        frames_seen[tid] += 1
                        label_for[tid] = model.names[int(cls_id)]

                        if tid in previous_center:
                            old_x, old_y = previous_center[tid]
                            distance = ((center_x - old_x) ** 2 + (center_y - old_y) ** 2) ** 0.5
                            total_distance[tid] += distance

                        previous_center[tid] = (center_x, center_y)

            frame_metrics.append({
                "frame": frame_idx,
                "time": round(frame_idx / fps, 2),
                "count": len(detections),
                "detections": detections,
            })

            writer.write(result.plot())

            if total_frames > 0:
                job["percent"] = int(((frame_idx + 1) / total_frames) * 100)

        cap.release()
        writer.release()

        tracks = [
            {
                "trackId": tid,
                "label": label_for.get(tid, "salamander"),
                "timeOnScreenSeconds": round(count / fps, 2),
                "framesSeen": count,
                "totalDistancePixels": round(total_distance[tid], 2),
            }
            for tid, count in frames_seen.items()
        ]

        job.clear()
        job["status"] = "done"
        job["percent"] = 100
        job["result"] = {
            "videoUrl": f"/video/{output_path.name}?t={int(time.time())}",
            "summary": {
                "totalFrames": len(frame_metrics),
                "framesWithDetections": sum(1 for frame in frame_metrics if frame["count"] > 0),
                "maxSimultaneousDetections": max_simultaneous,
            },
            "tracks": tracks,
            "metrics": frame_metrics,
        }

    except Exception as error:
        job.clear()
        job["status"] = "error"
        job["percent"] = 0
        job["message"] = str(error)


@app.post("/track")
async def start_track(video: UploadFile = File(...)):
    safe_filename = clean_filename(video.filename)

    input_path = UPLOAD_DIR / safe_filename
    output_path = OUTPUT_DIR / f"annotated_{safe_filename}"

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    job.clear()
    job["status"] = "processing"
    job["percent"] = 0

    Thread(
        target=run_track_job,
        args=(input_path, output_path),
        daemon=True,
    ).start()

    return {
        "status": "processing",
        "message": "Tracking job started.",
    }


@app.get("/track")
def get_track_status():
    return job


@app.get("/video/{filename}")
def get_video(filename: str):
    clean_name = filename.split("?")[0]
    file_path = OUTPUT_DIR / clean_name

    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=clean_name,
    )