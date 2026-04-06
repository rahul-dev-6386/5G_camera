import base64
from itertools import zip_longest

import cv2
import numpy as np


def _extract_histogram(frame_bgr: np.ndarray, bbox: list[int]) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    crop = frame_bgr[max(y1, 0):max(y2, 0), max(x1, 0):max(x2, 0)]
    if crop.size == 0:
        return np.zeros(48, dtype=np.float32)

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [8, 6], [0, 180, 0, 256])
    hist = cv2.normalize(hist, hist).flatten()
    return hist.astype(np.float32)


def _tile_images(images: list[np.ndarray]) -> bytes:
    resized: list[np.ndarray] = []
    for image in images:
        height, width = image.shape[:2]
        if width == 0 or height == 0:
            continue
        target_width = 640
        target_height = max(int(height * (target_width / width)), 1)
        resized.append(cv2.resize(image, (target_width, target_height)))

    if not resized:
        raise RuntimeError("No annotated images were available to compose.")

    rows: list[np.ndarray] = []
    for left, right in zip_longest(resized[::2], resized[1::2], fillvalue=None):
        if right is None:
            right = np.zeros_like(left)
        target_height = max(left.shape[0], right.shape[0])
        padded = []
        for image in (left, right):
            pad_bottom = target_height - image.shape[0]
            padded.append(cv2.copyMakeBorder(image, 0, pad_bottom, 0, 0, cv2.BORDER_CONSTANT, value=(15, 23, 42)))
        rows.append(np.hstack(padded))

    mosaic = rows[0] if len(rows) == 1 else np.vstack(rows)
    success, encoded = cv2.imencode(".jpg", mosaic)
    if not success:
        raise RuntimeError("Failed to encode the multi-camera mosaic.")
    return encoded.tobytes()


def _similarity_score(candidate: dict, existing: dict) -> float:
    anchor_distance = float(np.linalg.norm(candidate["anchor"] - existing["anchor"]))
    histogram_similarity = cv2.compareHist(candidate["histogram"], existing["histogram"], cv2.HISTCMP_CORREL)
    histogram_similarity = max(min(float(histogram_similarity), 1.0), -1.0)

    spatial_score = max(0.0, 1.0 - anchor_distance / 0.22)
    appearance_score = max(0.0, (histogram_similarity + 1.0) / 2.0)
    size_gap = abs(candidate["size"][0] - existing["size"][0]) + abs(candidate["size"][1] - existing["size"][1])
    size_score = max(0.0, 1.0 - size_gap / 0.35)
    return spatial_score * 0.45 + appearance_score * 0.4 + size_score * 0.15


def fuse_camera_detections(camera_results: list[dict]) -> dict:
    candidates: list[dict] = []
    camera_counts: dict[str, int] = {}
    annotated_images: list[np.ndarray] = []

    for index, camera_result in enumerate(camera_results):
        camera_id = camera_result["camera_id"]
        result = camera_result["result"]
        frame_bgr = result["frame_bgr"]
        camera_counts[camera_id] = result["count"]

        annotated = cv2.imdecode(np.frombuffer(result["annotated_bytes"], dtype=np.uint8), cv2.IMREAD_COLOR)
        if annotated is not None:
            label = f"{camera_id}: {result['count']} people"
            cv2.putText(annotated, label, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            annotated_images.append(annotated)

        for detection in result["detections"]:
            bbox = detection["bbox"]
            histogram = _extract_histogram(frame_bgr, bbox)
            anchor = np.array(detection["anchor"], dtype=np.float32)
            size = np.array(detection["size"], dtype=np.float32)
            candidates.append(
                {
                    "camera_id": camera_id,
                    "anchor": anchor,
                    "size": size,
                    "histogram": histogram,
                    "confidence": float(detection["confidence"]),
                    "bbox": bbox,
                    "camera_index": index,
                }
            )

    candidates.sort(key=lambda item: item["confidence"], reverse=True)
    fused_tracks: list[dict] = []

    for candidate in candidates:
        best_match_index = None
        best_score = 0.0

        for index, existing in enumerate(fused_tracks):
            if candidate["camera_id"] in existing["camera_ids"]:
                continue

            score = _similarity_score(candidate, existing)
            if score > best_score:
                best_score = score
                best_match_index = index

        if best_match_index is not None and best_score >= 0.62:
            existing = fused_tracks[best_match_index]
            existing["camera_ids"].append(candidate["camera_id"])
            existing["anchor"] = (existing["anchor"] + candidate["anchor"]) / 2
            existing["size"] = (existing["size"] + candidate["size"]) / 2
            existing["histogram"] = (existing["histogram"] + candidate["histogram"]) / 2
            existing["confidence"] = max(existing["confidence"], candidate["confidence"])
        else:
            fused_tracks.append(
                {
                    "camera_ids": [candidate["camera_id"]],
                    "anchor": candidate["anchor"],
                    "size": candidate["size"],
                    "histogram": candidate["histogram"],
                    "confidence": candidate["confidence"],
                }
            )

    mosaic_bytes = _tile_images(annotated_images)
    return {
        "count": len(fused_tracks),
        "camera_counts": camera_counts,
        "camera_count": len(camera_counts),
        "image_base64": base64.b64encode(mosaic_bytes).decode("utf-8"),
    }
