# Smart Campus Occupancy & Attendance System using AI + 5G Simulation

This project detects people from a webcam or uploaded frame with YOLOv8, counts occupancy, stores attendance-style records in local JSON files, and compares simulated 4G vs 5G latency plus edge-vs-cloud AI processing through a FastAPI backend and a professional React dashboard.

## Folder Structure

```text
apps/
  api/
    run_backend.sh
    src/
      app/
        config.py
        db.py
        main.py
        schemas.py
        security.py
        services/
          detector.py
          network.py
          stream_manager.py
  web/
    src/
      App.jsx
      index.css
      main.jsx
    .env.example
    index.html
    package.json
    vite.config.js
assets/
  models/
    README.md
    yolov8n.pt
scripts/
  check_project.sh
  run_backend.sh
storage/
  occupancy_logs.json
  refresh_sessions.json
  users.json
tools/
  video_stream_client.py
.env.example
requirements.txt
README.md
```

## Features

- Real-time YOLOv8 person-only detection
- Occupancy counting with annotated frames
- Attendance logging in local JSON storage with timestamp and count
- `/detect`, `/stats`, `/simulate-network`, and `/simulate-processing` FastAPI endpoints
- React dashboard with webcam, occupancy trend graph, network toggle, and responsive layout
- OpenCV webcam client for periodic frame uploads

## Installation

1. Create and activate a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements-cpu.txt
```

`requirements-cpu.txt` pins CPU-only PyTorch, which is the best fit for laptops without a dedicated NVIDIA GPU. If you already have a suitable CUDA setup, you can still use `requirements.txt`.

3. Copy the environment file and update it if needed:

```bash
cp .env.example .env
```

4. Create `.env` in the project root from `.env.example` and update it:

```env
STORAGE_DIR=/absolute/path/to/your/project/storage
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_ORIGIN=http://localhost:5173
JWT_SECRET_KEY=replace-with-a-long-random-secret
```

5. Set up the React frontend environment:

```bash
cp apps/web/.env.example apps/web/.env
```

If your backend runs on port `8000`, keep:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## How To Run

1. Start the FastAPI backend:

```bash
./scripts/run_backend.sh
```

2. Start the React frontend:

```bash
cd apps/web
npm install
npm run dev
```

3. Open the dashboard in your browser:

```text
http://localhost:5173
```

4. Click `Start Live Camera` to allow webcam access.

5. Switch between `5G` and `4G`, then compare `Edge` and `Cloud` AI paths to see the simulated latency difference.

6. Optional: build the React app for production and let FastAPI serve the built files:

```bash
./scripts/check_project.sh
```

7. Optional: run the OpenCV desktop webcam client instead of the browser camera:

```bash
python3 tools/video_stream_client.py --mode 5g --processing-mode edge --token <access-token>
```

## API Endpoints

### `POST /detect`

- Accepts an image frame as multipart form data with key `file`
- Optional query parameters: `mode=4g|5g` and `processing_mode=edge|cloud`
- Returns:

```json
{
  "count": 3,
  "timestamp": "2026-03-31T08:40:11.281276+00:00",
  "latency_ms": 126.2,
  "network_mode": "5g",
  "processing_mode": "edge",
  "network_delay_ms": 50.0,
  "processing_delay_ms": 35.0,
  "image_base64": "..."
}
```

### `GET /stats`

- Returns historical occupancy records from local JSON storage

### `GET /simulate-network?mode=4g`

- Simulates 300 ms latency for 4G

### `GET /simulate-network?mode=5g`

- Simulates 50 ms latency for 5G

### `GET /simulate-processing?mode=edge`

- Simulates an edge inference path with 35 ms processing delay

### `GET /simulate-processing?mode=cloud`

- Simulates a cloud inference path with 140 ms processing delay

## Sample Output Screenshots

### Dashboard View

- The top section has a polished glassmorphism-style control area with the project title, network mode selector, and camera start button.
- The main content area shows the raw camera feed beside the annotated YOLO detection frame.
- Summary cards display occupancy, detection timestamp, latency, and stream state.
- A dedicated attendance panel lists recent timestamped records from MongoDB.
- A responsive SVG analytics chart plots occupancy trends over time.

### 4G vs 5G + Edge vs Cloud Demo

- In `5G` mode, the status banner shows low-latency behavior and detection updates feel noticeably faster.
- In `4G` mode, the measured latency jumps to around 300 ms plus inference time, making the difference easy to demonstrate in class presentations.
- In `Edge` mode, the AI path stays close to the classroom workflow and keeps processing overhead low.
- In `Cloud` mode, the dashboard shows extra delay so you can explain the tradeoff between centralized processing and edge inference.

## Notes

- The first run may take longer because Ultralytics downloads `yolov8n.pt` if it is not already present in `assets/models/`.
- Data is stored locally in the folder configured by `STORAGE_DIR`, with separate JSON files for users, refresh sessions, and occupancy logs.
- If you use the browser dashboard, Chrome or Edge usually provide the smoothest webcam support.
- Keep your real `JWT_SECRET_KEY` only in `.env`, never in `.env.example` or committed source files.
- Run backend commands from the project root so the app uses the root `.venv` rather than any accidental virtual environment inside `apps/web/`.
