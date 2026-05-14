import { useState } from "react";
import axios from "axios";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
  const [videoFile, setVideoFile] = useState(null);
  const [result, setResult] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();

    if (!videoFile) {
      setError("Please choose a video first.");
      return;
    }

    setIsProcessing(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("video", videoFile);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/process-video`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      setResult(response.data);
    } catch (err) {
      console.error(err);
      setError("Something went wrong while processing the video.");
    } finally {
      setIsProcessing(false);
    }
  }

  const totalFrames = result?.metrics?.length || 0;
  const framesWithDetections =
    result?.metrics?.filter((frame) => frame.count > 0).length || 0;

  const maxCount =
    result?.metrics?.reduce((max, frame) => Math.max(max, frame.count), 0) || 0;

  const firstDetection = result?.metrics?.find(
    (frame) => frame.detections.length > 0
  )?.detections[0];

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">Applied AI Project</p>
        <h1>Salamander YOLO Tracker</h1>
        <p className="subtitle">
          Upload a salamander video, run YOLO detection, and view an annotated
          video with detection metrics.
        </p>
      </section>

      <section className="card">
        <h2>Upload Video</h2>

        <form onSubmit={handleSubmit} className="upload-form">
          <input
            type="file"
            accept="video/mp4,video/*"
            onChange={(event) => setVideoFile(event.target.files[0])}
          />

          <button type="submit" disabled={isProcessing}>
            {isProcessing ? "Processing..." : "Process Video"}
          </button>
        </form>

        {videoFile && <p className="file-name">Selected: {videoFile.name}</p>}
        {error && <p className="error">{error}</p>}
      </section>

      {result && (
        <>
          <section className="card">
            <h2>Annotated Video</h2>

            <video
              src={`${API_BASE_URL}${result.videoUrl}`}
              controls
              className="video-player"
            />
          </section>

          <section className="metrics-grid">
            <div className="metric-card">
              <h3>Total Frames</h3>
              <p>{totalFrames}</p>
            </div>

            <div className="metric-card">
              <h3>Frames With Detections</h3>
              <p>{framesWithDetections}</p>
            </div>

            <div className="metric-card">
              <h3>Max Salamanders On Screen</h3>
              <p>{maxCount}</p>
            </div>

            <div className="metric-card">
              <h3>Sample Coordinates</h3>
              {firstDetection ? (
                <p>
                  X: {firstDetection.centerX.toFixed(1)}, Y:{" "}
                  {firstDetection.centerY.toFixed(1)}
                </p>
              ) : (
                <p>No detections found</p>
              )}
            </div>
          </section>

          <section className="card">
            <h2>Detection Count Over Time</h2>

            <div className="timeline">
              {result.metrics.slice(0, 120).map((frame, index) => (
                <div
                  key={index}
                  className="timeline-bar"
                  title={`Frame ${index}: ${frame.count} detections`}
                  style={{
                    height: `${Math.max(8, frame.count * 28)}px`,
                  }}
                />
              ))}
            </div>

            <p className="note">
              Showing first 120 frames. Taller bars mean more salamanders
              detected in that frame.
            </p>
          </section>
        </>
      )}
    </main>
  );
}

export default App;