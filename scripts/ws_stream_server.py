import argparse
import asyncio
import time
from datetime import datetime

import cv2
import numpy as np
import websockets


def detect_people(frame: np.ndarray) -> int:
    """Placeholder detector for standalone demo mode.

    Replace this function with your model call if you need AI inference in this utility.
    """
    return 0


async def handle_client(websocket: websockets.WebSocketServerProtocol) -> None:
    buffer = bytearray()
    expected_size = None

    while True:
        try:
            chunk = await websocket.recv()
        except websockets.ConnectionClosed:
            break

        if isinstance(chunk, str):
            continue

        buffer.extend(chunk)

        while True:
            if expected_size is None:
                if len(buffer) < 4:
                    break
                expected_size = int.from_bytes(buffer[:4], byteorder="big")
                del buffer[:4]

            if len(buffer) < expected_size:
                break

            frame_bytes = bytes(buffer[:expected_size])
            del buffer[:expected_size]
            expected_size = None

            np_frame = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_frame, cv2.IMREAD_COLOR)
            if frame is None:
                await websocket.send("error: bad frame")
                continue

            count = detect_people(frame)
            ts = datetime.utcnow().isoformat() + "Z"
            await websocket.send(f"ok count={count} timestamp={ts}")


async def run_server(host: str, port: int) -> None:
    async with websockets.serve(handle_client, host, port, max_size=8 * 1024 * 1024):
        print(f"Server listening on ws://{host}:{port}")
        await asyncio.Future()


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone framed WebSocket stream server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8765, help="Bind port")
    args = parser.parse_args()

    asyncio.run(run_server(args.host, args.port))


if __name__ == "__main__":
    main()
