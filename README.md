# Smart Campus Occupancy and Attendance System (AI + 5G)

This project provides real-time person detection with YOLOv8/YOLOv10, occupancy analytics, attendance-style logging, and DeepSORT-based duplicate person tracking through a FastAPI backend and a professional React dashboard.

The current implementation is 5G-only, supports edge/cloud processing simulation, includes socket ingest for remote deployments, and features dynamic model selection with hardware-aware filtering.

## Folder Structure

```text
smart-campus-occupancy/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── config.py
│   │   ├── db.py              # Database abstraction (local JSON + MongoDB)
│   │   ├── mongodb_db.py      # MongoDB implementation
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── security.py
│   │   ├── services/
│   │   │   ├── detector.py
│   │   │   ├── ingest_manager.py
│   │   │   ├── multi_camera.py
│   │   │   ├── network.py
│   │   │   └── stream_manager.py
│   │   ├── middleware/
│   │   └── exceptions.py
│   ├── tests/
│   ├── run_backend.sh
│   └── requirements.txt
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   └── auth/
│   │   │       └── AuthView.jsx
│   │   ├── constants/
│   │   └── utils/
│   │       └── validation.js  # Zod validation schemas
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── models/                     # YOLO model files
│   ├── yolov8n.pt
│   ├── yolov8m.pt
│   ├── yolov8x.pt
│   ├── yolov10n.pt
│   ├── yolov10l.pt
│   └── yolov10x.pt
├── scripts/                    # Utility scripts
│   ├── run.sh
│   ├── check_project.sh
│   ├── camera_socket_client.py
│   ├── video_stream_client.py
│   └── ws_stream_client.py
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md
│   └── REPORT_TEMPLATE.md
├── docker/                     # Docker configurations
│   ├── docker-compose.yml
│   ├── docker-compose.production.yml
│   └── nginx.conf
├── storage/                    # Data storage (local JSON)
│   ├── users.json
│   ├── refresh_sessions.json
│   └── occupancy_logs.json
├── .env.example
├── .gitignore
├── docker-compose.yml          # Root-level convenience compose
├── Dockerfile                  # Backend Dockerfile
├── README.md
└── SETUP.md
```

## Features

- Real-time YOLOv8/YOLOv10 person-only detection with dynamic model selection
- DeepSORT-based duplicate person tracking with multiple Re-ID embedders (MobileNet, CLIP variants)
- Occupancy counting with annotated frames and unique person identification
- Attendance logging with flexible storage (local JSON or MongoDB)
- JWT-based auth (signup, login, refresh, logout) with Zod validation
- Stream modes: browser webcam, direct camera URL pull, multi-camera pull, and socket ingest push
- Multi-camera fusion to reduce duplicate counts across overlapping feeds
- Hardware-aware model filtering (GPU/CPU detection)
- `/detect`, `/stream/*`, `/multi-stream/*`, `/ingest/*`, `/stats`, `/models` API endpoints
- Professional React dashboard with sidebar navigation, dark/light theme, and responsive design
- OpenCV utility clients for periodic upload and socket ingest streaming
- Model selection UI for detection models and Re-ID embedders
- Database status monitoring with automatic fallback to local JSON storage

## Installation

1. Create and activate a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies (GPU):

```bash
cd backend
pip install -r requirements-gpu.txt
```

For CPU-only environments:

```bash
cd backend
pip install -r requirements.txt
```

`requirements-gpu.txt` includes DeepSORT and CLIP for advanced tracking features.

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
JWT_SECRET_KEY=replace-with-a-long-random-secret-at-least-32-chars
YOLO_MODEL=auto
YOLO_CONFIDENCE=0.35
YOLO_IOU=0.45
YOLO_IMGSZ=960
YOLO_DEVICE=auto
ENABLE_TRACKING=true
TRACKING_MAX_AGE=30

# Database Configuration (optional)
# Set ENABLE_MONGODB=true to use MongoDB instead of local JSON storage
# If using MongoDB Atlas, ensure your IP is whitelisted in Network Access settings
# IMPORTANT: URL-encode special characters in password (@ becomes %40, : becomes %3A)
ENABLE_MONGODB=false
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=smart_campus
```

5. Set up the React frontend environment:

```bash
cd frontend
npm install
```

For local development, keep the default proxy setting in `frontend/.env`:

```env
VITE_API_BASE_URL=/api
```

## How To Run

### Quick Start (Using Scripts)

```bash
# Start both backend and frontend in development mode
./scripts/run.sh dev

# Start backend only
./scripts/run.sh backend

# Start frontend only
./scripts/run.sh frontend

# Start Docker environment
./scripts/run.sh docker

# Start Docker production environment
./scripts/run.sh docker-prod
```

### Manual Start

1. Start the FastAPI backend:

```bash
cd backend
bash run_backend.sh
```

Or manually:
```bash
cd /path/to/5G_camera
PYTHONPATH=. python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. Start the React frontend:

```bash
cd frontend
npm install
npm run dev
```

3. Open the dashboard in your browser:

```text
http://localhost:5173
```

4. Click `Start Live Camera` to allow webcam access.

5. Choose processing mode (`Edge` or `Cloud`) and capture source (`Browser Camera`, `Direct Stream`, `Socket Ingest`).

6. Optional: build the React app for production and let FastAPI serve the built files:

```bash
./scripts/check_project.sh
```

7. Optional: run the OpenCV desktop webcam uploader client instead of the browser camera:

```bash
python3 scripts/video_stream_client.py --processing-mode edge --token <access-token>
```

8. Optional: for private LAN cameras that remote servers cannot reach directly, push frames via WebSocket ingest:

```bash
python3 scripts/camera_socket_client.py \
  --ws-url ws://localhost:8000/ws/ingest/cam_1 \
  --stream-url http://10.0.13.153:8081/video \
  --stream-username admin \
  --stream-password admin \
  --token <access-token>
```

To push your laptop webcam instead of an IP stream URL:

```bash
python3 scripts/camera_socket_client.py \
  --ws-url ws://localhost:8000/ws/ingest/laptop_cam \
  --stream-device 0 \
  --token <access-token>
```

Then in the frontend select `Capture Source -> Socket Ingest`, refresh ingest cameras, and start ingest monitoring.

## Standalone Framed WebSocket Demo

These utilities are for generic socket-style streaming tests independent of app auth/routes.

Start framed websocket server:

```bash
python3 scripts/ws_stream_server.py --host 0.0.0.0 --port 8765
```

Push local webcam with length-prefixed frames:

```bash
python3 scripts/ws_stream_client.py --ws-url ws://127.0.0.1:8765 --stream-device 0 --fps 10
```

Push RTSP/HTTP stream URL:

```bash
python3 scripts/ws_stream_client.py --ws-url ws://127.0.0.1:8765 --stream-url rtsp://user:pass@camera-ip:554/stream1
```

## Quick Start For Lightning / Remote Backend

If backend runs remotely (for example in Lightning) and camera is on your laptop/LAN:

1. Keep backend running remotely.
2. Open frontend through forwarded port (for example `5173`).
3. Run `scripts/camera_socket_client.py` from the machine that can access the camera (your laptop/LAN host).
4. Use backend websocket URL and your JWT access token.

This avoids direct backend-to-private-camera routing problems.

## API Endpoints

### `POST /detect`

- Accepts an image frame as multipart form data with key `file`
- Optional query parameters: `mode=5g` and `processing_mode=edge|cloud`
- Returns:

```json
{
  "count": 3,
  "unique_count": 3,
  "timestamp": "2026-03-31T08:40:11.281276+00:00",
  "latency_ms": 126.2,
  "network_mode": "5g",
  "processing_mode": "edge",
  "network_delay_ms": 50.0,
  "processing_delay_ms": 35.0,
  "image_base64": "..."
}
```

### `GET /models`

- Returns available detection models and Re-ID embedders with hardware requirements
- Includes current model selection and tracking status

```json
{
  "available_models": {
    "yolov8n.pt": {"name": "YOLOv8 Nano", "requires_gpu": false},
    "yolov8m.pt": {"name": "YOLOv8 Medium", "requires_gpu": true},
    "yolov10n.pt": {"name": "YOLOv10 Nano", "requires_gpu": false}
  },
  "current_model": "yolov8m.pt",
  "hardware_info": {"has_gpu": true, "gpu_name": "RTX 3080"},
  "tracking_enabled": true,
  "available_reid_embedders": ["mobilenet", "clip_resnet50"],
  "current_reid_embedder": "mobilenet"
}
```

### `POST /models/select`

- Dynamically switch the detection model
- Request body: `{"model": "yolov10n.pt"}`

### `POST /models/reid`

- Dynamically switch the Re-ID embedder for DeepSORT tracking
- Request body: `{"embedder": "clip_resnet50"}`

### `GET /stats`

- Returns historical occupancy records from local JSON storage

### `GET /simulate-network?mode=5g`

- Simulates 50 ms latency for 5G

### `GET /simulate-processing?mode=edge`

- Simulates an edge inference path with 35 ms processing delay

### `GET /simulate-processing?mode=cloud`

- Simulates a cloud inference path with 140 ms processing delay

## Dashboard Notes

- The control section supports auth context, classroom/course selection, source selection, processing mode, and theme toggle.
- The live section shows source frame, detection result, and status metrics including latency and camera counts.
- The analytics section visualizes occupancy trend and recent attendance logs.
- Socket ingest status can display all connected ingest cameras for monitoring and fusion.

## Notes

- The first run may take longer because Ultralytics downloads the configured model (default: `auto`) if it is not already present in `models/`.
- Data is stored locally in the folder configured by `STORAGE_DIR` (JSON files) or in MongoDB if configured.
- If you use the browser dashboard, Chrome or Edge usually provide the smoothest webcam support.
- Keep your real `JWT_SECRET_KEY` only in `.env`, never in `.env.example` or committed source files.
- Run backend commands from the project root so the app uses the root `.venv` rather than any accidental virtual environment inside `frontend/`.
- MongoDB connection requires proper IP whitelisting in Atlas Network Access settings if using MongoDB Atlas.
- Special characters in MongoDB passwords must be URL-encoded (e.g., `@` → `%40`, `:` → `%3A`).
- The system automatically falls back to local JSON storage if MongoDB connection fails.

### Detector Tuning

- Use `YOLO_MODEL=auto` for automatic hardware-aware selection, or specify a model directly
- Available models: `yolov8n.pt`, `yolov8m.pt`, `yolov8l.pt`, `yolov8x.pt`, `yolov10n.pt`, `yolov10l.pt`, `yolov10x.pt`
- Use `YOLO_DEVICE=auto` to choose CUDA when available and CPU otherwise.
- Increase `YOLO_IMGSZ` for better small-object detection, reduce it for faster inference.
- Increase `YOLO_CONFIDENCE` to reduce false positives, decrease it to detect more candidates.
- Enable `ENABLE_TRACKING=true` for DeepSORT-based duplicate person tracking.
- Choose Re-ID embedder via UI: `mobilenet` (faster, CPU-friendly) or `clip_resnet50` (more accurate, GPU recommended).

### Lightning AI / Remote Deployment

For deploying on Lightning AI or other cloud platforms with local cameras:

1. Use **ngrok** to expose your camera stream publicly:
   ```bash
   ngrok tcp 192.168.x.x:554  # For RTSP
   ngrok http 192.168.x.x:8080  # For HTTP
   ```

2. Use the ngrok public URL in the Lightning AI application

3. Alternatively, use **socket ingest** to push frames from your local network:
   ```bash
   python3 scripts/camera_socket_client.py \
     --ws-url ws://your-lightning-ai-url.com/ws/ingest/cam_1 \
     --stream-url http://192.168.x.x:8081/video \
     --token <access-token>
   ```

### Report Generation

Use the provided markdown template to document project work:

```bash
cp docs/REPORT_TEMPLATE.md docs/PROJECT_REPORT.md
```

Fill in the sections with your project details, architecture, performance metrics, testing results, and future enhancements.
