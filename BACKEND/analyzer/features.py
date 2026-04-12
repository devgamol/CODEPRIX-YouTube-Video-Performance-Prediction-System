import math
import os
from typing import Dict, List

import cv2

try:
    import torch
    import clip as clip_lib
except Exception:
    torch = None
    clip_lib = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import mediapipe as mp
except Exception:
    mp = None

_CLIP_DEVICE = "cpu"
_CLIP_MODEL = None
_CLIP_PREPROCESS = None
_CLIP_TEXT_FEATURES = None
_POS_PROMPTS = [
    "an engaging presenter speaking to camera",
    "a clear expressive talking face",
    "high quality social media video frame",
    "dynamic and visually appealing frame",
]
_NEG_PROMPTS = [
    "a dull empty frame",
    "blurry low quality video frame",
    "dark unengaging scene",
    "visual clutter and distraction",
]

if torch is not None and clip_lib is not None and Image is not None:
    try:
        _CLIP_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        _CLIP_MODEL, _CLIP_PREPROCESS = clip_lib.load("ViT-B/32", device=_CLIP_DEVICE)
        text_tokens = clip_lib.tokenize(_POS_PROMPTS + _NEG_PROMPTS).to(_CLIP_DEVICE)
        with torch.no_grad():
            _CLIP_TEXT_FEATURES = _CLIP_MODEL.encode_text(text_tokens)
            _CLIP_TEXT_FEATURES = _CLIP_TEXT_FEATURES / _CLIP_TEXT_FEATURES.norm(dim=-1, keepdim=True)
    except Exception:
        _CLIP_MODEL = None
        _CLIP_PREPROCESS = None
        _CLIP_TEXT_FEATURES = None

_FACE_DETECTOR = None
if mp is not None:
    try:
        _FACE_DETECTOR = mp.solutions.face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.5,
        )
    except Exception:
        _FACE_DETECTOR = None


def _resolve_keyframe_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.normpath(path)


def _clip_score_for_image(image_path: str) -> float:
    if _CLIP_MODEL is None or _CLIP_PREPROCESS is None or _CLIP_TEXT_FEATURES is None or Image is None:
        return 0.5

    if not os.path.exists(image_path):
        return 0.5

    try:
        image = Image.open(image_path).convert("RGB")
        image_tensor = _CLIP_PREPROCESS(image).unsqueeze(0).to(_CLIP_DEVICE)

        with torch.no_grad():
            image_features = _CLIP_MODEL.encode_image(image_tensor)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            similarity = (100.0 * image_features @ _CLIP_TEXT_FEATURES.T).squeeze(0)

        positive_scores = similarity[: len(_POS_PROMPTS)]
        negative_scores = similarity[len(_POS_PROMPTS) :]

        pos_mean = float(positive_scores.mean().item())
        neg_mean = float(negative_scores.mean().item())
        raw_score = pos_mean - neg_mean

        normalized = 1.0 / (1.0 + math.exp(-(raw_score / 8.0)))
        return max(0.0, min(1.0, normalized))
    except Exception:
        return 0.5


def _face_data_for_image(scene_index: int, image_path: str) -> Dict:
    fallback = {
        "scene_index": scene_index,
        "face_detected": False,
        "face_count": 0,
        "confidence": 0.0,
        "face_prominence": 0.0,
    }

    if _FACE_DETECTOR is None:
        return fallback

    frame = cv2.imread(image_path)
    if frame is None:
        return fallback

    try:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = _FACE_DETECTOR.process(rgb)
        detections = results.detections if results and results.detections else []

        if not detections:
            return fallback

        h, w = frame.shape[:2]
        confidences = []
        prominences = []

        for detection in detections:
            score = float(detection.score[0]) if detection.score else 0.0
            confidences.append(score)

            bbox = detection.location_data.relative_bounding_box
            area = max(0.0, float(bbox.width)) * max(0.0, float(bbox.height))
            pixel_area = area * float(w * h)
            prominence = pixel_area / float(w * h) if w > 0 and h > 0 else 0.0
            prominences.append(max(0.0, min(1.0, prominence)))

        return {
            "scene_index": scene_index,
            "face_detected": True,
            "face_count": len(detections),
            "confidence": float(sum(confidences) / len(confidences)) if confidences else 0.0,
            "face_prominence": float(max(prominences)) if prominences else 0.0,
        }
    except Exception:
        return fallback


def analyze_features(video_data) -> Dict[str, List[Dict]]:
    scenes = video_data.get("scenes", []) if isinstance(video_data, dict) else []

    clip_scores = []
    face_data = []

    for idx, scene in enumerate(scenes):
        scene_index = int(scene.get("index", idx))
        scene_start = float(scene.get("start", 0.0))
        scene_end = float(scene.get("end", scene_start))

        keyframe_path = _resolve_keyframe_path(str(scene.get("keyframe_path", "")))
        clip_score = _clip_score_for_image(keyframe_path)

        clip_scores.append(
            {
                "scene_index": scene_index,
                "scene_start": scene_start,
                "scene_end": scene_end,
                "clip_score": clip_score,
            }
        )

        face_data.append(_face_data_for_image(scene_index, keyframe_path))

    return {
        "clip_scores": clip_scores,
        "face_data": face_data,
    }
