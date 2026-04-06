import base64
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO


MODEL_DIR = Path(__file__).resolve().parents[5] / "assets" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


class PersonDetector:
    def __init__(self) -> None:
        model_path = MODEL_DIR / "yolov8n.pt"
        # Use a local weight file when present, otherwise fall back to the
        # pretrained Ultralytics checkpoint name so it can be downloaded once.
        self.model = YOLO(str(model_path if model_path.exists() else "yolov8n.pt"))

    def detect_people(self, image_bytes: bytes) -> dict:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        frame_height, frame_width = frame.shape[:2]

        results = self.model.predict(frame, verbose=False)
        annotated = frame.copy()
        count = 0
        detections: list[dict] = []

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
            raise RuntimeError("Failed to encode annotated image")

        annotated_bytes = encoded.tobytes()

        return {
            "count": count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "image_base64": base64.b64encode(annotated_bytes).decode("utf-8"),
            "annotated_bytes": annotated_bytes,
            "frame_shape": [frame_height, frame_width],
            "detections": detections,
            "frame_bgr": frame,
        }


detector = PersonDetector()
