from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from ultralytics import YOLO
import cv2
import shutil
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

model = YOLO("models/best.pt")


@app.get("/")
def home():
    return {"message": "Salamander YOLO FastAPI Backend Running"}


@app.post("/process-video")
async def process_video(video: UploadFile = File(...)):

    # Clean filename
    safe_filename = (
        video.filename
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
    )

    input_path = os.path.join(
        UPLOAD_FOLDER,
        safe_filename
    )

    output_filename = f"annotated_{safe_filename}"

    output_path = os.path.join(
        OUTPUT_FOLDER,
        output_filename
    )

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    cap = cv2.VideoCapture(input_path)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Browser-friendly codec
    fourcc = cv2.VideoWriter_fourcc(*"avc1")

    out = cv2.VideoWriter(
        output_path,
        fourcc,
        fps,
        (width, height)
    )

    frame_data = []

    while True:

        success, frame = cap.read()

        if not success:
            break

        results = model(frame)

        annotated_frame = results[0].plot()

        boxes = results[0].boxes

        detections = []

        count = 0

        if boxes is not None:

            for box in boxes:

                x1, y1, x2, y2 = box.xyxy[0].tolist()

                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2

                detections.append({
                    "centerX": center_x,
                    "centerY": center_y
                })

                count += 1

        frame_data.append({
            "count": count,
            "detections": detections
        })

        out.write(annotated_frame)

    cap.release()
    out.release()

    return {
        "videoUrl": f"/video/{output_filename}",
        "metrics": frame_data
    }


@app.get("/video/{filename}")
def get_video(filename: str):

    file_path = os.path.join(OUTPUT_FOLDER, filename)

    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=filename
    )