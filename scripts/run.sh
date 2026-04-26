#!/usr/bin/env bash

# Smart Campus Occupancy System - Main Run Script
# Usage: ./scripts/run.sh [dev|prod|backend|frontend|docker]

set -euo pipefail

cd "$(dirname "$0")/.."

case "${1:-dev}" in
  dev)
    echo "Starting development environment..."
    # Start backend in background
    cd backend && bash run_backend.sh &
    BACKEND_PID=$!
    
    # Start frontend
    cd ../frontend && npm install && npm run dev
    ;;
  backend)
    echo "Starting backend only..."
    cd backend && bash run_backend.sh
    ;;
  frontend)
    echo "Starting frontend only..."
    cd frontend && npm install && npm run dev
    ;;
  docker)
    echo "Starting Docker environment..."
    cd docker && docker-compose up --build
    ;;
  docker-prod)
    echo "Starting Docker production environment..."
    cd docker && docker-compose -f docker-compose.production.yml up --build
    ;;
  *)
    echo "Usage: $0 [dev|backend|frontend|docker|docker-prod]"
    echo "  dev        - Start both backend and frontend in development mode"
    echo "  backend    - Start backend only"
    echo "  frontend   - Start frontend only"
    echo "  docker     - Start Docker development environment"
    echo "  docker-prod - Start Docker production environment"
    exit 1
    ;;
esac
