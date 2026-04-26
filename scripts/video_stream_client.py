import argparse
import time
from datetime import datetime

import cv2
import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Webcam client for Smart Campus occupancy detection")
    parser.add_argument("--api", default="http://localhost:8000/detect", help="FastAPI detect endpoint")
    parser.add_argument("--mode", choices=["5g"], default="5g", help="Network simulation mode")
    parser.add_argument("--processing-mode", choices=["edge", "cloud"], default="edge", help="AI processing path")
    parser.add_argument("--token", required=True, help="JWT access token for the dashboard user")
    parser.add_argument("--classroom", default="Room 101", help="Classroom label for stored logs")
    parser.add_argument("--course-code", default="CSE101", help="Course code for stored logs")
    parser.add_argument("--interval", type=float, default=3.0, help="Seconds between frame uploads")
    args = parser.parse_args()

    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        raise RuntimeError("Unable to open webcam.")

    last_sent = 0.0
    latest_result = {"count": 0, "latency_ms": 0.0, "timestamp": ""}

    try:
        while True:
            success, frame = camera.read()
            if not success:
                break

            now = time.time()
            if now - last_sent >= args.interval:
                success, encoded = cv2.imencode(".jpg", frame)
                if success:
                    response = requests.post(
                        f"{args.api}?mode={args.mode}&processing_mode={args.processing_mode}&classroom={args.classroom}&course_code={args.course_code}",
                        files={"file": ("frame.jpg", encoded.tobytes(), "image/jpeg")},
                        headers={"Authorization": f"Bearer {args.token}"},
                        timeout=60,
                    )
                    response.raise_for_status()
                    latest_result = response.json()
                    last_sent = now

            cv2.putText(
                frame,
                f"Occupancy: {latest_result['count']}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                frame,
                f"Latency: {latest_result['latency_ms']} ms | {args.mode.upper()} | {args.processing_mode.upper()}",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )
            if latest_result["timestamp"]:
                readable = datetime.fromisoformat(latest_result["timestamp"].replace("Z", "+00:00"))
                cv2.putText(
                    frame,
                    f"Last log: {readable.strftime('%H:%M:%S')}",
                    (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

            cv2.imshow("Smart Campus Occupancy Client", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
