# Setup Guide

This guide will help you set up and run the Smart Campus Occupancy and Attendance System on your local machine.

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- npm or yarn
- Git
- (Optional) GPU with CUDA support for faster inference

## Quick Start

### Option 1: Using the Run Script (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd 5G_camera

# Start both backend and frontend
./scripts/run.sh dev
```

This will:
1. Start the FastAPI backend on http://localhost:8000
2. Start the React frontend on http://localhost:5173
3. Open your browser to http://localhost:5173

### Option 2: Docker (Easiest)

```bash
# Clone the repository
git clone <repository-url>
cd 5G_camera

# Start all services with Docker
docker-compose up --build
```

## Manual Setup

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd 5G_camera
```

### Step 2: Backend Setup

```bash
# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# On Linux/Mac:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
cd backend

# For GPU support (recommended)
pip install -r requirements-gpu.txt

# For CPU-only
pip install -r requirements.txt

# Go back to project root
cd ..
```

### Step 3: Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Required minimum changes:
# - JWT_SECRET_KEY: Set to a long random string (at least 32 characters)
# - STORAGE_DIR: Set to absolute path to your project storage folder
```

Example `.env`:
```env
STORAGE_DIR=/absolute/path/to/your/project/storage
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_ORIGIN=http://localhost:5173
JWT_SECRET_KEY=your-very-long-random-secret-key-at-least-32-chars-long
YOLO_MODEL=auto
YOLO_CONFIDENCE=0.35
YOLO_IOU=0.45
YOLO_IMGSZ=960
YOLO_DEVICE=auto
ENABLE_TRACKING=true

# Database Configuration (optional)
# Set ENABLE_MONGODB=true to use MongoDB instead of local JSON storage
# If using MongoDB Atlas, ensure your IP is whitelisted in Network Access settings
# IMPORTANT: URL-encode special characters in password (@ becomes %40, : becomes %3A)
ENABLE_MONGODB=false
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=smart_campus
```

### Step 4: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create frontend environment file (optional)
echo "VITE_API_BASE_URL=/api" > .env

# Go back to project root
cd ..
```

### Step 5: Download YOLO Models

The system will automatically download models on first run, but you can also download them manually:

```bash
# Models will be downloaded to models/ directory
# Available models:
# - yolov8n.pt (Nano - fastest, good for CPU)
# - yolov8m.pt (Medium - balanced)
# - yolov8x.pt (Extra Large - most accurate, requires GPU)
# - yolov10n.pt (YOLOv10 Nano)
# - yolov10l.pt (YOLOv10 Large)
# - yolov10x.pt (YOLOv10 Extra Large)
```

### Step 6: Start the Application

**Start Backend:**
```bash
cd backend
bash run_backend.sh
```

Or manually:
```bash
cd /path/to/5G_camera
PYTHONPATH=. python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Start Frontend (new terminal):**
```bash
cd frontend
npm run dev
```

**Access the Application:**
Open http://localhost:5173 in your browser

## First-Time Use

1. **Create an Account:**
   - Click "Sign Up" on the login screen
   - Enter username (min 3 chars), password (min 8 chars with uppercase, lowercase, and digit), and full name (min 5 chars)
   - Click "Sign Up"

2. **Log In:**
   - Enter your username and password
   - Click "Login"

3. **Check Database Status:**
   - The login page shows database connection status (Local JSON or MongoDB)
   - Green indicator indicates active connection
   - If MongoDB fails, system automatically falls back to local JSON storage

4. **Start Detection:**
   - Click "Start Live Camera"
   - Allow browser camera access when prompted
   - Select processing mode:
     - **Edge**: Simulates edge processing (~35ms delay)
     - **Cloud**: Simulates cloud processing (~140ms delay)
   - Select capture source:
     - **Browser Camera**: Use your webcam
     - **Direct Stream**: Connect to an IP/RTSP camera
     - **Socket Ingest**: For remote camera streaming

## Troubleshooting

### Backend won't start

**Issue:** Port 8000 already in use
```bash
# Kill process using port 8000
# On Linux/Mac:
lsof -ti:8000 | xargs kill -9
# On Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Issue:** Module not found
```bash
# Make sure you're in the project root
cd /path/to/5G_camera
source .venv/bin/activate
cd backend
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend won't start

**Issue:** Port 5173 already in use
```bash
# Kill process using port 5173
# On Linux/Mac:
lsof -ti:5173 | xargs kill -9
# On Windows:
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

**Issue:** npm install fails
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Camera not working

**Issue:** Browser camera not accessible
- Make sure you're using HTTPS or localhost
- Check browser camera permissions
- Try a different browser (Chrome/Edge recommended)

**Issue:** IP camera not connecting
- Verify the camera URL is correct
- Check if camera is on the same network
- Test camera URL in VLC player first
- Check camera username/password

### Model download issues

**Issue:** Models not downloading
- Check internet connection
- Manual download models from Ultralytics releases
- Place .pt files in `models/` directory

## Advanced Configuration

### Using MongoDB instead of JSON files

Edit `.env`:
```env
ENABLE_MONGODB=true
MONGODB_URI=mongodb://localhost:27017
# For MongoDB Atlas:
# IMPORTANT: URL-encode special characters in password (@ becomes %40, : becomes %3A)
# Example: mongodb+srv://username:password%40123@cluster.mongodb.net
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net
MONGODB_DB_NAME=smart_campus
```

**MongoDB Atlas Setup:**
1. Create a free MongoDB Atlas account
2. Create a new cluster
3. Go to Network Access and add your IP address (or use `0.0.0.0/0` for all IPs)
4. Go to Database Access and create a database user
5. Get your connection string from the Connect button
6. URL-encode special characters in your password if needed
7. Update `.env` with the connection string

**Note:** If MongoDB connection fails, the system automatically falls back to local JSON storage.

### Using an external camera via Socket Ingest

On your camera machine:
```bash
python3 scripts/camera_socket_client.py \
  --ws-url ws://localhost:8000/ws/ingest/cam_1 \
  --stream-url http://192.168.x.x:8081/video \
  --stream-username admin \
  --stream-password admin \
  --token <your-access-token>
```

Then in the dashboard:
1. Select "Socket Ingest" as capture source
2. Click "Refresh Ingest Cameras"
3. Select your camera
4. Click "Start Live Camera"

### Changing YOLO Model

Edit `.env`:
```env
YOLO_MODEL=yolov8m.pt  # or yolov8n.pt, yolov8x.pt, yolov10n.pt, etc.
```

Or change it dynamically in the dashboard:
1. Go to Overview view
2. Find Model Selection section
3. Choose from available models

### Adjusting Detection Sensitivity

Edit `.env`:
```env
YOLO_CONFIDENCE=0.35  # Lower to detect more, higher to reduce false positives
YOLO_IOU=0.45        # IoU threshold for NMS
```

## Development

### Running Tests

**Backend tests:**
```bash
cd backend
pytest tests/ -v
```

**Frontend tests:**
```bash
cd frontend
npm test
```

### Linting

**Backend:**
```bash
cd backend
flake8 app/
black app/
isort app/
```

**Frontend:**
```bash
cd frontend
npm run lint
```

## Production Deployment

### Using Docker Compose (Production)

```bash
cd docker
docker-compose -f docker-compose.production.yml up --build
```

This includes:
- Backend with health checks
- Frontend
- MongoDB
- Nginx reverse proxy

### Environment Variables for Production

Create a production `.env` file:
```env
STORAGE_DIR=/app/storage
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_ORIGIN=https://your-domain.com
JWT_SECRET_KEY=<strong-random-secret-at-least-32-chars>
JWT_ACCESS_EXP_MINUTES=15
JWT_REFRESH_EXP_DAYS=7
YOLO_MODEL=auto
YOLO_CONFIDENCE=0.35
YOLO_IOU=0.45
YOLO_IMGSZ=960
YOLO_DEVICE=auto
ENABLE_TRACKING=true
TRACKING_MAX_AGE=30
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=/app/logs
REQUEST_TIMEOUT=30
MAX_UPLOAD_SIZE=10485760
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
MIN_PASSWORD_LENGTH=8
ENABLE_MONGODB=true
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DB_NAME=smart_campus
```

## Getting Help

- Check the [README.md](README.md) for detailed documentation
- Check [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system architecture
- Check [docs/REPORT_TEMPLATE.md](docs/REPORT_TEMPLATE.md) for reporting guidelines

## Next Steps

1. Run the application and try the browser camera
2. Explore different processing modes (Edge/Cloud)
3. Try connecting an IP camera
4. Experiment with different YOLO models
5. Enable DeepSORT tracking for unique person counting
6. View analytics and occupancy trends
