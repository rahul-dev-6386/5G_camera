import argparse
import asyncio
import time

import cv2
import websockets


async def stream_camera(ws_url: str, stream_url: str, stream_device: int | None, fps: float, jpeg_quality: int) -> None:
    source = stream_device if stream_device is not None else stream_url
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera source")

    frame_interval = max(1.0 / max(fps, 0.5), 0.02)
    quality = min(max(jpeg_quality, 40), 95)

    async with websockets.connect(ws_url, max_size=8 * 1024 * 1024) as ws:
        print(f"Connected to {ws_url}")
        while True:
            started = time.perf_counter()
            ok, frame = cap.read()
            if not ok:
                await asyncio.sleep(0.1)
                continue

            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            if not ok:
                continue

            payload = encoded.tobytes()
            length_prefix = len(payload).to_bytes(4, byteorder="big")
            await ws.send(length_prefix + payload)

            try:
                reply = await asyncio.wait_for(ws.recv(), timeout=2.0)
                print("Server:", reply)
            except asyncio.TimeoutError:
                print("No ack from server")

            elapsed = time.perf_counter() - started
            delay = max(frame_interval - elapsed, 0.0)
            if delay > 0:
                await asyncio.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone framed WebSocket stream client")
    parser.add_argument("--ws-url", default="ws://127.0.0.1:8765", help="WebSocket URL")
    parser.add_argument("--stream-url", default="", help="IP/RTSP stream URL")
    parser.add_argument("--stream-device", type=int, default=None, help="Local webcam index")
    parser.add_argument("--fps", type=float, default=10.0, help="Frame rate")
    parser.add_argument("--jpeg-quality", type=int, default=80, help="JPEG quality")
    args = parser.parse_args()

    if args.stream_device is None and not args.stream_url:
        parser.error("Provide either --stream-url or --stream-device")

    asyncio.run(
        stream_camera(
            ws_url=args.ws_url,
            stream_url=args.stream_url,
            stream_device=args.stream_device,
            fps=args.fps,
            jpeg_quality=args.jpeg_quality,
        )
    )


if __name__ == "__main__":
    main()
