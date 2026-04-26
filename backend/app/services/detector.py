import base64
import warnings
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
import torch
from deep_sort_realtime.deepsort_tracker import DeepSort
from PIL import Image
from ultralytics import YOLO

# Suppress floating point and NumPy warnings
warnings.filterwarnings("ignore", category=UserWarning, message=".*float.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*invalid value.*")
warnings.filterwarnings("ignore", message=".*FP16.*")
warnings.filterwarnings("ignore", message=".*half precision.*")

from ..config import get_settings
from ..logger import get_logger


MODEL_DIR = Path(__file__).resolve().parents[3] / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
settings = get_settings()
logger = get_logger(__name__)


def detect_hardware_capabilities() -> dict:
    """Detect hardware capabilities and return optimal model selection."""
    has_gpu = torch.cuda.is_available()
    
    if has_gpu:
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
        
        logger.info(f"GPU detected: {gpu_name} with {gpu_memory:.2f} GB memory")
        
        # Select model based on GPU memory
        if gpu_memory >= 12:  # High-end GPU (RTX 3080+, A100, etc.)
            return {
                "has_gpu": True,
                "gpu_name": gpu_name,
                "gpu_memory_gb": gpu_memory,
                "recommended_model": "yolov8x.pt",  # Extra large
                "device": "cuda:0"
            }
        elif gpu_memory >= 8:  # Mid-range GPU (RTX 3070, 2080, etc.)
            return {
                "has_gpu": True,
                "gpu_name": gpu_name,
                "gpu_memory_gb": gpu_memory,
                "recommended_model": "yolov8l.pt",  # Large
                "device": "cuda:0"
            }
        elif gpu_memory >= 6:  # Entry-level GPU (RTX 3060, 2060, etc.)
            return {
                "has_gpu": True,
                "gpu_name": gpu_name,
                "gpu_memory_gb": gpu_memory,
                "recommended_model": "yolov8m.pt",  # Medium
                "device": "cuda:0"
            }
        else:  # Low-end GPU (GTX 1650, integrated GPU, etc.)
            return {
                "has_gpu": True,
                "gpu_name": gpu_name,
                "gpu_memory_gb": gpu_memory,
                "recommended_model": "yolov8s.pt",  # Small
                "device": "cuda:0"
            }
    else:
        logger.info("No GPU detected, using CPU")
        # For CPU, use the smallest model for best performance
        return {
            "has_gpu": False,
            "gpu_name": None,
            "gpu_memory_gb": 0,
            "recommended_model": "yolov8n.pt",  # Nano (fastest on CPU)
            "device": "cpu"
        }


def get_available_models() -> dict:
    """Get list of available models with their requirements."""
    hardware = detect_hardware_capabilities()
    
    models = {
        "yolov8n.pt": {
            "name": "YOLOv8 Nano",
            "size": "nano",
            "params": "3.2M",
            "speed": "Fastest",
            "accuracy": "Good",
            "requires_gpu": False,
            "recommended_for": ["CPU", "Edge devices", "Real-time"]
        },
        "yolov8s.pt": {
            "name": "YOLOv8 Small",
            "size": "small",
            "params": "11.2M",
            "speed": "Fast",
            "accuracy": "Better",
            "requires_gpu": False,
            "recommended_for": ["CPU", "Low-end GPU", "Real-time"]
        },
        "yolov8m.pt": {
            "name": "YOLOv8 Medium",
            "size": "medium",
            "params": "25.9M",
            "speed": "Medium",
            "accuracy": "Good",
            "requires_gpu": False,
            "recommended_for": ["Mid-range GPU", "Balanced performance"]
        },
        "yolov8l.pt": {
            "name": "YOLOv8 Large",
            "size": "large",
            "params": "43.7M",
            "speed": "Slow",
            "accuracy": "Better",
            "requires_gpu": True,
            "recommended_for": ["High-end GPU", "Accuracy priority"]
        },
        "yolov8x.pt": {
            "name": "YOLOv8 Extra Large",
            "size": "xlarge",
            "params": "68.2M",
            "speed": "Slowest",
            "accuracy": "Best",
            "requires_gpu": True,
            "recommended_for": ["High-end GPU", "Maximum accuracy"]
        },
        "yolov9c.pt": {
            "name": "YOLOv9 Compact",
            "size": "compact",
            "params": "25.3M",
            "speed": "Medium",
            "accuracy": "Excellent",
            "requires_gpu": False,
            "recommended_for": ["Mid-range GPU", "Better accuracy"]
        },
        "yolov9e.pt": {
            "name": "YOLOv9 Enhanced",
            "size": "enhanced",
            "params": "57.4M",
            "speed": "Slow",
            "accuracy": "Excellent",
            "requires_gpu": True,
            "recommended_for": ["High-end GPU", "Accuracy priority"]
        },
        "yolov10n.pt": {
            "name": "YOLOv10 Nano",
            "size": "nano",
            "params": "2.3M",
            "speed": "Fastest",
            "accuracy": "Good+",
            "requires_gpu": False,
            "recommended_for": ["CPU", "Edge devices", "Real-time", "NMS-free"]
        },
        "yolov10s.pt": {
            "name": "YOLOv10 Small",
            "size": "small",
            "params": "7.1M",
            "speed": "Fast",
            "accuracy": "Better+",
            "requires_gpu": False,
            "recommended_for": ["CPU", "Low-end GPU", "NMS-free"]
        },
        "yolov10m.pt": {
            "name": "YOLOv10 Medium",
            "size": "medium",
            "params": "15.6M",
            "speed": "Medium",
            "accuracy": "Excellent",
            "requires_gpu": False,
            "recommended_for": ["Mid-range GPU", "Balanced", "NMS-free"]
        },
        "yolov10l.pt": {
            "name": "YOLOv10 Large",
            "size": "large",
            "params": "22.6M",
            "speed": "Slow",
            "accuracy": "Excellent+",
            "requires_gpu": True,
            "recommended_for": ["High-end GPU", "Accuracy priority", "NMS-free"]
        },
        "yolov10x.pt": {
            "name": "YOLOv10 Extra Large",
            "size": "xlarge",
            "params": "29.5M",
            "speed": "Slowest",
            "accuracy": "Best",
            "requires_gpu": True,
            "recommended_for": ["High-end GPU", "Maximum accuracy", "NMS-free"]
        },
    }
    
    # Re-identification embedders for duplicate person detection
    reid_embedders = {
        "mobilenet": {
            "name": "MobileNet v2",
            "description": "Lightweight, fast, good for CPU",
            "speed": "Fastest",
            "accuracy": "Good",
            "requires_gpu": False,
            "recommended_for": ["CPU", "Edge", "Real-time"]
        },
        "clip_ViT-B/32": {
            "name": "CLIP ViT-B/32",
            "description": "Vision Transformer, excellent re-identification",
            "speed": "Medium",
            "accuracy": "Excellent",
            "requires_gpu": True,
            "recommended_for": ["GPU", "Best re-id accuracy"]
        },
        "clip_ViT-B/16": {
            "name": "CLIP ViT-B/16",
            "description": "Larger ViT, superior feature extraction",
            "speed": "Slow",
            "accuracy": "Best",
            "requires_gpu": True,
            "recommended_for": ["High-end GPU", "Maximum re-id accuracy"]
        },
        "clip_RN50": {
            "name": "CLIP ResNet-50",
            "description": "ResNet backbone, balanced speed/accuracy",
            "speed": "Medium",
            "accuracy": "Very Good",
            "requires_gpu": True,
            "recommended_for": ["GPU", "Balanced re-id"]
        },
        "clip_RN101": {
            "name": "CLIP ResNet-101",
            "description": "Deeper ResNet, better features",
            "speed": "Slow",
            "accuracy": "Excellent",
            "requires_gpu": True,
            "recommended_for": ["High-end GPU", "Better re-id"]
        },
    }
    
    # Filter models based on hardware
    available_models = {}
    for model_id, model_info in models.items():
        if not model_info["requires_gpu"] or hardware["has_gpu"]:
            available_models[model_id] = model_info
    
    # Filter re-id embedders based on hardware
    available_reid = {}
    for embedder_id, embedder_info in reid_embedders.items():
        if not embedder_info["requires_gpu"] or hardware["has_gpu"]:
            available_reid[embedder_id] = embedder_info
    
    return {
        "hardware": hardware,
        "available_models": available_models,
        "available_reid_embedders": available_reid,
        "current_model": detector.get_current_model() if detector else settings.yolo_model,
        "current_reid_embedder": detector.current_embedder if detector else "mobilenet",
        "tracking_enabled": detector.enable_tracking if detector else settings.enable_tracking,
    }


class PersonDetector:
    def __init__(self) -> None:
        self.model = None
        self.device = None
        self.enable_tracking = False
        self.tracker = None
        self.current_model_name = None
        self.current_embedder = "mobilenet"
        self._load_model(settings.yolo_model.strip() or "auto")
    
    def _load_model(self, model_name: str) -> None:
        """Load a specific model."""
        # Handle auto model selection
        if model_name == "auto":
            hardware_info = detect_hardware_capabilities()
            configured_model = hardware_info["recommended_model"]
            logger.info(f"Auto-selected model: {configured_model} based on hardware capabilities")
            logger.info(f"Hardware info: GPU={hardware_info['has_gpu']}, Memory={hardware_info['gpu_memory_gb']:.2f}GB")
        else:
            configured_model = model_name
        
        model_path = MODEL_DIR / configured_model
        # Use local weights when present; otherwise let Ultralytics resolve/download once.
        self.model = YOLO(str(model_path if model_path.exists() else configured_model))
        self.device = self._resolve_device(settings.yolo_device)
        self.current_model_name = configured_model
        
        # Apply quantization if on CPU for better performance
        if self.device == "cpu":
            try:
                self.model.fuse()
                logger.info("Model fused for CPU inference")
            except Exception as e:
                logger.warning(f"Could not fuse model: {e}")
        
        # Initialize DeepSORT tracker for person tracking
        self.enable_tracking = settings.enable_tracking
        if self.enable_tracking:
            self._init_tracker(self.current_embedder)
        
        logger.info(f"Model loaded: {configured_model} on device: {self.device}")
    
    def _init_tracker(self, embedder: str) -> None:
        """Initialize the DeepSORT tracker with a specific re-id embedder."""
        try:
            self.tracker = DeepSort(
                max_age=settings.max_age,
                n_init=3,
                nn_budget=100,
                embedder=embedder,
                nms_max_overlap=0.3
            )
            self.current_embedder = embedder
            logger.info(f"DeepSORT tracker initialized with embedder={embedder}, max_age={settings.max_age}")
        except Exception as e:
            logger.warning(f"Could not initialize DeepSORT tracker with {embedder}: {e}")
            # Fallback to mobilenet
            if embedder != "mobilenet":
                try:
                    self.tracker = DeepSort(
                        max_age=settings.max_age,
                        n_init=3,
                        nn_budget=100,
                        embedder="mobilenet",
                        nms_max_overlap=0.3
                    )
                    self.current_embedder = "mobilenet"
                    logger.info("Fallback: DeepSORT tracker initialized with mobilenet embedder")
                except Exception as e2:
                    logger.warning(f"Could not initialize DeepSORT tracker: {e2}")
                    self.enable_tracking = False
            else:
                self.enable_tracking = False
    
    def switch_model(self, model_name: str) -> bool:
        """Switch to a different model."""
        try:
            self._load_model(model_name)
            return True
        except Exception as e:
            logger.error(f"Failed to switch model to {model_name}: {e}")
            return False
    
    def switch_embedder(self, embedder_name: str) -> bool:
        """Switch the re-identification embedder."""
        try:
            self._init_tracker(embedder_name)
            return True
        except Exception as e:
            logger.error(f"Failed to switch embedder to {embedder_name}: {e}")
            return False
    
    def get_current_model(self) -> str:
        """Get the current model name."""
        return self.current_model_name
    
    def get_current_embedder(self) -> str:
        """Get the current re-id embedder name."""
        return self.current_embedder

    @staticmethod
    def _resolve_device(configured_device: str) -> str:
        requested = (configured_device or "auto").strip().lower()
        if requested == "auto":
            return "cuda:0" if torch.cuda.is_available() else "cpu"
        if requested.startswith("cuda") and not torch.cuda.is_available():
            return "cpu"
        return requested

    def detect_people(self, image_bytes: bytes) -> dict:
        """Detect people in a single image with optional tracking."""
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        frame_height, frame_width = frame.shape[:2]

        results = self.model.predict(
            frame,
            verbose=False,
            conf=settings.yolo_confidence,
            iou=settings.yolo_iou,
            imgsz=settings.yolo_imgsz,
            device=self.device,
        )
        annotated = frame.copy()
        count = 0
        detections: list[dict] = []
        unique_ids: set = set()

        # Prepare detections for DeepSORT
        yolo_detections = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                if self.model.names[class_id] != "person":
                    continue

                x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
                confidence = float(box.conf[0].item())
                yolo_detections.append(([x1, y1, x2 - x1, y2 - y1], confidence, "person"))

        # Apply DeepSORT tracking if enabled
        if self.enable_tracking and yolo_detections:
            tracks = self.tracker.update_tracks(yolo_detections, frame=frame)
            for track in tracks:
                if not track.is_confirmed():
                    continue
                
                track_id = track.track_id
                unique_ids.add(track_id)
                ltrb = track.to_ltwh()
                x1, y1, w, h = [int(v) for v in ltrb]
                x2, y2 = x1 + w, y1 + h
                confidence = track.det_conf if hasattr(track, 'det_conf') else 0.0
                
                count += 1
                width = max(x2 - x1, 1)
                height = max(y2 - y1, 1)
                anchor_x = (x1 + x2) / 2
                anchor_y = y2

                detections.append(
                    {
                        "bbox": [x1, y1, x2, y2],
                        "confidence": round(confidence, 4),
                        "anchor": [round(anchor_x / frame_width, 4), round(anchor_y / frame_height, 4)],
                        "size": [round(width / frame_width, 4), round(height / frame_height, 4)],
                        "track_id": track_id,
                    }
                )

                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 200, 0), 2)
                cv2.putText(
                    annotated,
                    f"ID:{track_id}",
                    (x1, max(y1 - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 200, 0),
                    2,
                )
        else:
            # Fallback to YOLO-only detection
            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0].item())
                    if self.model.names[class_id] != "person":
                        continue

                    count += 1
                    x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
                    confidence = float(box.conf[0].item())
                    width = max(x2 - x1, 1)
                    height = max(y2 - y1, 1)
                    anchor_x = (x1 + x2) / 2
                    anchor_y = y2

                    detections.append(
                        {
                            "bbox": [x1, y1, x2, y2],
                            "confidence": round(confidence, 4),
                            "anchor": [round(anchor_x / frame_width, 4), round(anchor_y / frame_height, 4)],
                            "size": [round(width / frame_width, 4), round(height / frame_height, 4)],
                        }
                    )

                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 200, 0), 2)
                    cv2.putText(
                        annotated,
                        f"person {confidence:.2f}",
                        (x1, max(y1 - 8, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 200, 0),
                        2,
                    )

        # Use unique count if tracking is enabled
        unique_count = len(unique_ids) if self.enable_tracking else count

        cv2.putText(
            annotated,
            f"Occupancy: {unique_count}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            3,
        )

        success, encoded = cv2.imencode(".jpg", annotated)
        if not success:
            raise RuntimeError("Failed to encode annotated image")

        annotated_bytes = encoded.tobytes()

        return {
            "count": unique_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "image_base64": base64.b64encode(annotated_bytes).decode("utf-8"),
            "annotated_bytes": annotated_bytes,
            "frame_shape": [frame_height, frame_width],
            "detections": detections,
            "frame_bgr": frame,
            "tracking_enabled": self.enable_tracking,
        }

    def detect_people_batch(self, images_bytes: List[bytes]) -> List[dict]:
        """Detect people in multiple images using batch processing for better performance."""
        if not images_bytes:
            return []
        
        # Preprocess all images
        frames = []
        for image_bytes in images_bytes:
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            frames.append(frame)
        
        # Run batch prediction
        results = self.model.predict(
            frames,
            verbose=False,
            conf=settings.yolo_confidence,
            iou=settings.yolo_iou,
            imgsz=settings.yolo_imgsz,
            device=self.device,
            batch=True,
        )
        
        # Process results
        outputs = []
        for i, (result, frame) in enumerate(zip(results, frames)):
            frame_height, frame_width = frame.shape[:2]
            annotated = frame.copy()
            count = 0
            detections: list[dict] = []

            for box in result.boxes:
                class_id = int(box.cls[0].item())
                if self.model.names[class_id] != "person":
                    continue

                count += 1
                x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
                confidence = float(box.conf[0].item())
                width = max(x2 - x1, 1)
                height = max(y2 - y1, 1)
                anchor_x = (x1 + x2) / 2
                anchor_y = y2

                detections.append(
                    {
                        "bbox": [x1, y1, x2, y2],
                        "confidence": round(confidence, 4),
                        "anchor": [round(anchor_x / frame_width, 4), round(anchor_y / frame_height, 4)],
                        "size": [round(width / frame_width, 4), round(height / frame_height, 4)],
                    }
                )

                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 200, 0), 2)
                cv2.putText(
                    annotated,
                    f"person {confidence:.2f}",
                    (x1, max(y1 - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 200, 0),
                    2,
                )

            cv2.putText(
                annotated,
                f"Occupancy: {count}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                3,
            )

            success, encoded = cv2.imencode(".jpg", annotated)
            if not success:
                logger.error(f"Failed to encode annotated image for batch item {i}")
                continue

            annotated_bytes = encoded.tobytes()

            outputs.append({
                "count": count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "image_base64": base64.b64encode(annotated_bytes).decode("utf-8"),
                "annotated_bytes": annotated_bytes,
                "frame_shape": [frame_height, frame_width],
                "detections": detections,
                "frame_bgr": frame,
            })
        
        logger.info(f"Batch processed {len(outputs)} images")
        return outputs


detector = PersonDetector()
