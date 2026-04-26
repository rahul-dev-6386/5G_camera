# Smart Campus Occupancy System - Architecture Documentation

## System Overview

The Smart Campus Occupancy and Attendance System is a real-time person detection and analytics platform built with:
- **Backend**: FastAPI (Python) with YOLOv8/YOLOv10 for AI-powered person detection
- **Frontend**: React with Vite for the professional dashboard with sidebar navigation
- **Database**: MongoDB (optional) or local JSON file storage
- **AI/ML**: DeepSORT for duplicate person tracking with multiple Re-ID embedders
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **Deployment**: Docker containers with docker-compose orchestration

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Browser    │  │  Mobile App  │  │  Camera Feed │          │
│  │  (React UI)  │  │   (Future)   │  │   (RTSP/HTTP)│          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          │ HTTP/HTTPS       │                  │
          │ WebSocket        │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           FastAPI Application (Port 8000)                 │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        │  │
│  │  │   Auth     │  │  Detection │  │  Streaming │        │  │
│  │  │ Middleware │  │  Endpoints │  │ Endpoints  │        │  │
│  │  └────────────┘  └────────────┘  └────────────┘        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        │  │
│  │  │ Rate Limit │  │   Metrics  │  │   Logging  │        │  │
│  │  └────────────┘  └────────────┘  └────────────┘        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ PersonDetector│  │StreamManager │  │AlertManager  │         │
│  │   (YOLOv8)   │  │  (OpenCV)    │  │ (Thresholds) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │AnalyticsSvc  │  │FrameBuffer   │  │RateLimiter   │         │
│  │ (Time-series)│  │  (Jitter)    │  │  (In-memory) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   MongoDB    │  │  Local JSON  │  │  Storage     │         │
│  │  (Optional)  │  │   Files      │  │  (Frames)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Monitoring & Observability                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Prometheus  │  │   Grafana    │  │  Structured  │         │
│  │   Metrics    │  │  Dashboards  │  │    Logs      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### Backend Services

#### 1. Authentication Service
- **JWT-based authentication** with access and refresh tokens
- **Password strength validation** with configurable requirements (uppercase, lowercase, digit)
- **Zod validation** on frontend for real-time form validation feedback
- **Rate limiting** on auth endpoints to prevent brute force attacks
- **Session management** with automatic token expiration
- **Token refresh** mechanism with automatic token rotation

#### 2. Detection Service
- **YOLOv8/YOLOv10 models** for real-time person detection
- **Dynamic model selection** with hardware-aware filtering (GPU/CPU)
- **Available models**: YOLOv8n/m/l/x, YOLOv10n/l
- **DeepSORT integration** for duplicate person tracking
- **Multiple Re-ID embedders**: MobileNet, CLIP ResNet50/ViT-B/32
- **Model optimization** with quantization and fusion for CPU inference
- **Batch processing** support for multiple frames
- **Configurable confidence** and IOU thresholds

#### 3. Stream Management Service
- **Multi-protocol support**: RTSP, HTTP, WebSocket ingest
- **Auto-reconnection** with configurable retry logic
- **Health monitoring** with status tracking
- **Frame buffer queues** for network jitter handling

#### 4. Analytics Service
- **Time-series aggregation** for occupancy trends
- **Peak occupancy analysis** with configurable time windows
- **Classroom comparison** across multiple locations
- **Hourly heatmap** generation for pattern analysis

#### 5. Alert Service
- **Capacity threshold alerts** with configurable limits
- **Severity levels**: Info, Warning, Critical
- **Callback system** for custom alert handling
- **Alert history** with summary statistics

### Frontend Components

#### 1. React Dashboard
- **Professional UI** with sidebar navigation and top header bar
- **Real-time occupancy display** with live updates
- **Camera stream viewer** with multiple stream modes (Browser Camera, Direct Stream, Socket Ingest)
- **Detection visualization** with annotated frames
- **Analytics charts** for trends and patterns
- **Dark/Light theme** with persistent preference
- **Model selection UI** for detection models and Re-ID embedders
- **Hardware status badges** (GPU/CPU mode, tracking status)
- **Responsive design** for mobile and desktop

#### 2. Authentication UI
- **User registration** with Zod validation and inline error display
- **Login form** with session management
- **Database status indicator** showing MongoDB/Local JSON connection
- **Token refresh** handling with automatic rotation
- **Logout functionality**
- **Real-time validation feedback** with visual error indicators

### Data Storage

#### MongoDB (Optional)
- **Connection pooling** with configurable pool sizes (max: 50, min: 5)
- **Automatic indexing** on frequently queried fields
- **TTL indexes** for session expiration
- **Replica set support** for high availability
- **URL encoding** for special characters in credentials (@ → %40, : → %3A)
- **Automatic fallback** to local JSON storage on connection failure
- **Async operations** using Motor driver for non-blocking I/O
- **Startup/shutdown handlers** for proper connection management

#### Local JSON Storage
- **File-based persistence** for development/testing
- **MongoDB-compatible API** for easy migration
- **Atomic write operations** with error handling

### Monitoring Stack

#### Prometheus Metrics
- **HTTP request metrics**: count, duration, status codes
- **Detection metrics**: count, duration, people count
- **Camera metrics**: connections, errors, health status
- **Database metrics**: operation count, duration
- **Auth metrics**: attempts, success/failure rates
- **Alert metrics**: count by severity and type

#### Grafana Dashboards
- **System health overview**
- **API performance metrics**
- **Detection accuracy and latency**
- **Camera connection status**
- **Alert history and trends**

## Data Flow

### Detection Flow
```
1. Camera Frame Capture
   ↓
2. Frame Buffer (Jitter Handling)
   ↓
3. YOLOv8/YOLOv10 Inference (Edge/Cloud)
   ↓
4. DeepSORT Tracking (if enabled)
   ↓
5. Unique Person Counting
   ↓
6. Detection Processing
   ↓
7. Occupancy Logging
   ↓
8. Alert Check (Thresholds)
   ↓
9. Response to Client
```

### Authentication Flow
```
1. User Credentials
   ↓
2. Rate Limit Check
   ↓
3. Password Validation
   ↓
4. Database Lookup
   ↓
5. Token Generation (JWT)
   ↓
6. Session Persistence
   ↓
7. Response with Tokens
```

### Stream Management Flow
```
1. Stream Connection Request
   ↓
2. URL Parsing & Sanitization
   ↓
3. OpenCV VideoCapture Init
   ↓
4. Frame Reading Loop
   ↓
5. Health Monitoring
   ↓
6. Auto-Reconnection (if needed)
   ↓
7. Frame Delivery to Client
```

## Security Considerations

### Authentication & Authorization
- **JWT tokens** with short-lived access tokens (15 min)
- **Refresh tokens** with longer expiration (7 days)
- **Password hashing** using PBKDF2 with 100,000 iterations
- **Rate limiting** to prevent brute force attacks

### Data Protection
- **Input validation** on all endpoints
- **SQL injection prevention** through parameterized queries
- **XSS protection** via Content Security Policy headers
- **CORS configuration** for controlled cross-origin access

### Network Security
- **HTTPS/TLS** for all communications (production)
- **WebSocket security** with authentication
- **API key management** for external integrations
- **Network segmentation** for database access

## Deployment Architecture

### Development Environment
```
- Local Python environment with virtualenv
- Local React dev server (Vite)
- Local JSON file storage
- Manual configuration via .env file
```

### Production Environment
```
- Docker containers for all services
- Docker Compose for orchestration
- MongoDB for data persistence
- Nginx reverse proxy
- Prometheus + Grafana for monitoring
```

### Scalability Considerations
- **Horizontal scaling** of API instances behind load balancer
- **Database sharding** for large-scale deployments
- **CDN integration** for static assets
- **Message queue** for async processing (future)

## Performance Optimization

### Backend Optimizations
- **Model quantization** for faster CPU inference
- **Batch processing** for multiple frame detection
- **Connection pooling** for database access
- **Frame buffering** to handle network jitter
- **Async I/O** for concurrent request handling

### Frontend Optimizations
- **Code splitting** for faster initial load
- **Image optimization** for faster transmission
- **WebSocket** for real-time updates
- **Caching strategy** for static assets
- **Lazy loading** for heavy components

## Monitoring & Alerting

### Key Metrics
- **API response time** (p50, p95, p99)
- **Detection latency** (end-to-end)
- **Camera connection health**
- **Error rates** by endpoint
- **System resource utilization**

### Alert Thresholds
- **API error rate** > 5%
- **Detection latency** > 2 seconds
- **Camera disconnection** > 1 minute
- **Database operation timeout** > 5 seconds
- **System memory** > 80%

## Future Enhancements

### Planned Features
- **Zone-based counting** for area-specific occupancy
- **Mobile app** for on-the-go monitoring
- **Integration** with campus scheduling systems
- **Historical analytics** with trend prediction
- **Real-time alerts** for capacity violations
- **Heatmap generation** for occupancy patterns
- **Face recognition** integration
- **Cloud-native deployment** with auto-scaling

### Technical Improvements
- **GPU acceleration** for Re-ID embedders
- **Edge deployment** for reduced latency
- **Real-time video analytics** pipeline
- **Machine learning** for occupancy prediction
- **Multi-tenant support** for campus-wide deployment
- **Model quantization** for edge deployment
- **Message queue** for async processing
