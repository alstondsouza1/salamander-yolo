import { useState } from "react";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
  const [videoFile, setVideoFile] = useState(null);
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("idle");
  const [percent, setPercent] = useState(0);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();

    if (!videoFile) {
      setError("Please choose a video first.");
      return;
    }

    setStatus("processing");
    setPercent(0);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("video", videoFile);

    try {
      const uploadResponse = await fetch(`${API_BASE_URL}/track`, {
        method: "POST",
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error("Upload failed.");
      }

      pollJobStatus();
    } catch (err) {
      console.error(err);
      setError("Something went wrong while uploading the video.");
      setStatus("error");
    }
  }

  function pollJobStatus() {
    const intervalId = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/track`);
        const data = await response.json();

        setStatus(data.status);
        setPercent(data.percent || 0);

        if (data.status === "done") {
          clearInterval(intervalId);
          setResult(data.result);
          setPercent(100);
        }

        if (data.status === "error") {
          clearInterval(intervalId);
          setError(data.message || "Tracking failed.");
        }
      } catch (err) {
        clearInterval(intervalId);
        console.error(err);
        setError("Could not check job progress.");
        setStatus("error");
      }
    }, 1000);
  }

  const totalFrames = result?.summary?.totalFrames || 0;
  const framesWithDetections = result?.summary?.framesWithDetections || 0;
  const maxCount = result?.summary?.maxSimultaneousDetections || 0;

  const firstDetection = result?.metrics?.find(
    (frame) => frame.detections.length > 0
  )?.detections[0];

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">Applied AI Project</p>
        <h1>Salamander YOLO Tracker</h1>
        <p className="subtitle">
          Upload a video, run YOLO tracking, and view an annotated video with
          per-salamander metrics.
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

          <button type="submit" disabled={status === "processing"}>
            {status === "processing" ? "Processing..." : "Process Video"}
          </button>
        </form>

        {videoFile && <p className="file-name">Selected: {videoFile.name}</p>}

        {status === "processing" && (
          <div className="progress-area">
            <p>Processing video... {percent}%</p>
            <progress value={percent} max="100"></progress>
          </div>
        )}

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
            <h2>Per-Salamander Metrics</h2>

            <table className="tracks-table">
              <thead>
                <tr>
                  <th>Track ID</th>
                  <th>Label</th>
                  <th>Time on Screen</th>
                  <th>Frames Seen</th>
                  <th>Total Distance</th>
                </tr>
              </thead>

              <tbody>
                {result.tracks.map((track) => (
                  <tr key={track.trackId}>
                    <td>{track.trackId}</td>
                    <td>{track.label}</td>
                    <td>{track.timeOnScreenSeconds}s</td>
                    <td>{track.framesSeen}</td>
                    <td>{track.totalDistancePixels}px</td>
                  </tr>
                ))}
              </tbody>
            </table>
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