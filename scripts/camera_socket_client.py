import argparse
import asyncio
import time
from urllib.parse import quote, urlsplit, urlunsplit

import cv2
import websockets


def build_authenticated_url(stream_url: str, username: str, password: str) -> str:
    if not username:
        return stream_url

    parsed = urlsplit(stream_url)
    if not parsed.scheme or not parsed.netloc:
        return stream_url

    hostname = parsed.hostname or ""
    if not hostname:
        return stream_url
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"

    port = f":{parsed.port}" if parsed.port else ""
    auth = quote(username, safe="")
    if password:
        auth = f"{auth}:{quote(password, safe='')}"
    netloc = f"{auth}@{hostname}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def open_capture(args: argparse.Namespace) -> cv2.VideoCapture:
    if args.stream_device is not None:
        return cv2.VideoCapture(int(args.stream_device))

    capture_url = build_authenticated_url(args.stream_url, args.stream_username, args.stream_password)
    return cv2.VideoCapture(capture_url)


async def stream_frames(args: argparse.Namespace) -> None:
    camera = open_capture(args)
    if not camera.isOpened():
        raise RuntimeError("Unable to open stream URL. Check reachability and credentials.")

    frame_interval = max(1.0 / max(args.fps, 0.5), 0.05)
    quality = min(max(args.jpeg_quality, 40), 95)

    ws_url = f"{args.ws_url}?token={args.token}"
    async with websockets.connect(ws_url, max_size=8 * 1024 * 1024) as websocket:
        print(f"Connected: {ws_url}")
        try:
            while True:
                started = time.perf_counter()
                ok, frame = camera.read()
                if not ok:
                    await asyncio.sleep(0.2)
                    continue

                encode_ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                if not encode_ok:
                    continue

                await websocket.send(encoded.tobytes())
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2.0)
                except Exception:
                    pass

                elapsed = time.perf_counter() - started
                delay = max(frame_interval - elapsed, 0)
                if delay > 0:
                    await asyncio.sleep(delay)
        finally:
            camera.release()


def main() -> None:
    parser = argparse.ArgumentParser(description="Push camera frames to Lightning backend over WebSocket.")
    parser.add_argument("--ws-url", required=True, help="WebSocket ingest endpoint, e.g. ws://localhost:8000/ws/ingest/cam_1")
    parser.add_argument("--stream-url", default="", help="Camera stream URL, e.g. http://10.0.13.153:8081/video")
    parser.add_argument("--stream-device", type=int, default=None, help="Local webcam index, e.g. 0")
    parser.add_argument("--token", required=True, help="Dashboard access token (JWT access token)")
    parser.add_argument("--stream-username", default="", help="Optional stream username")
    parser.add_argument("--stream-password", default="", help="Optional stream password")
    parser.add_argument("--fps", type=float, default=5.0, help="Frame push rate")
    parser.add_argument("--jpeg-quality", type=int, default=80, help="JPEG quality 40-95")
    args = parser.parse_args()

    if args.stream_device is None and not args.stream_url:
        parser.error("Provide either --stream-url or --stream-device.")

    asyncio.run(stream_frames(args))


if __name__ == "__main__":
    main()
