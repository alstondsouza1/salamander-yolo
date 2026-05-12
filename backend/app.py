from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from ultralytics import YOLO
import cv2
import os

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

model = YOLO("models/best.pt")


@app.route("/")
def home():
    return {"message": "Salamander YOLO Backend Running"}


@app.route("/process-video", methods=["POST"])
def process_video():

    if "video" not in request.files:
        return jsonify({"error": "No video uploaded"}), 400

    video = request.files["video"]

    input_path = os.path.join(UPLOAD_FOLDER, video.filename)
    output_path = os.path.join(OUTPUT_FOLDER, f"annotated_{video.filename}")

    video.save(input_path)

    cap = cv2.VideoCapture(input_path)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

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

        results = model(frame, conf=0.15, verbose=False)

        detections = []

        annotated_frame = results[0].plot()

        boxes = results[0].boxes

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

    return jsonify({
        "videoUrl": f"/video/{os.path.basename(output_path)}",
        "metrics": frame_data
    })


@app.route("/video/<filename>")
def get_video(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True)