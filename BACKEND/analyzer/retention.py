import numpy as np

from config import (
    LONG_SCENE_PENALTY_WEIGHT,
    LOW_MOTION_PENALTY_WEIGHT,
    MOTION_LOW_THRESHOLD,
    NO_SPEECH_PROB_THRESHOLD,
    SILENCE_PENALTY_WEIGHT,
)


def _build_runs(seconds):
    if not seconds:
        return []

    runs = []
    start = seconds[0]
    prev = seconds[0]

    for second in seconds[1:]:
        if second == prev + 1:
            prev = second
            continue

        runs.append((start, prev))
        start = second
        prev = second

    runs.append((start, prev))
    return runs


def _merge_runs_with_small_gaps(runs, max_gap):
    if not runs:
        return []

    merged = [runs[0]]
    for start, end in runs[1:]:
        last_start, last_end = merged[-1]
        gap = start - last_end - 1
        if gap < max_gap:
            merged[-1] = (last_start, end)
        else:
            merged.append((start, end))

    return merged


def _segment_stats(retention_curve, start, end):
    points = [p for p in retention_curve if start <= int(p["time"]) <= end]
    if not points:
        return {
            "avg_retention": 0.0,
            "avg_motion": 0.0,
            "avg_energy": 0.0,
            "silence_ratio": 1.0,
            "avg_scene_age": 0.0,
            "avg_no_speech": 1.0,
        }

    avg_retention = float(np.mean([p["retention"] for p in points]))
    avg_motion = float(np.mean([p["signals"]["motion"] for p in points]))
    avg_energy = float(np.mean([p["signals"]["energy"] for p in points]))
    silence_ratio = float(np.mean([1.0 if p["signals"]["silence"] else 0.0 for p in points]))
    avg_scene_age = float(np.mean([p["signals"]["scene_age"] for p in points]))
    avg_no_speech = float(np.mean([p["signals"]["no_speech_confidence"] for p in points]))

    return {
        "avg_retention": avg_retention,
        "avg_motion": avg_motion,
        "avg_energy": avg_energy,
        "silence_ratio": silence_ratio,
        "avg_scene_age": avg_scene_age,
        "avg_no_speech": avg_no_speech,
    }


def _dominant_signal(stats, mode):
    if mode == "weak":
        motion_risk = 0.0
        if MOTION_LOW_THRESHOLD > 0:
            motion_risk = max(0.0, (MOTION_LOW_THRESHOLD - stats["avg_motion"]) / MOTION_LOW_THRESHOLD)

        energy_risk = max(0.0, (0.3 - stats["avg_energy"]) / 0.3)
        silence_risk = stats["silence_ratio"]
        scene_age_risk = min(1.0, stats["avg_scene_age"])

        if NO_SPEECH_PROB_THRESHOLD < 1.0:
            no_speech_risk = max(
                0.0,
                (stats["avg_no_speech"] - NO_SPEECH_PROB_THRESHOLD) / (1.0 - NO_SPEECH_PROB_THRESHOLD),
            )
        else:
            no_speech_risk = 0.0

        scores = {
            "motion": motion_risk,
            "energy": energy_risk,
            "silence": silence_risk,
            "scene_age": scene_age_risk,
            "no_speech_confidence": no_speech_risk,
        }
    else:
        # For strong segments, prioritize positive engagement drivers.
        scores = {
            "motion": max(0.0, min(1.0, stats["avg_motion"])) * 1.2,
            "energy": max(0.0, min(1.0, stats["avg_energy"])) * 1.2,
            "silence": max(0.0, min(1.0, 1.0 - stats["silence_ratio"])) * 0.6,
            "no_speech_confidence": max(0.0, min(1.0, 1.0 - stats["avg_no_speech"])) * 0.6,
        }

    return max(scores, key=scores.get)


def _weak_severity(avg_retention):
    if avg_retention < 40:
        return "high"
    if avg_retention < 55:
        return "medium"
    return "low"


def compute_retention_analysis(video_data, audio_data):
    motion_lookup = {}
    for item in video_data.get("motion_scores", []):
        second = int(float(item.get("timestamp", 0)))
        motion_lookup[second] = float(item.get("motion_intensity", 0.0))

    energy_lookup = {}
    for item in audio_data.get("energy_curve", []):
        second = int(float(item.get("timestamp", 0)))
        energy_lookup[second] = float(item.get("energy", 0.0))

    silence_lookup = {}
    for key, value in audio_data.get("silence_map", {}).items():
        silence_lookup[int(key)] = bool(value)

    scene_age_lookup = {}
    for scene in video_data.get("scenes", []):
        start = int(float(scene.get("start", 0.0)))
        end = int(float(scene.get("end", 0.0)))

        for second in range(start, end + 1):
            age = max(0.0, float(second) - float(scene.get("start", 0.0)))
            scene_age_lookup[second] = age / 45.0

    no_speech_lookup = {}
    for segment in audio_data.get("transcription", []):
        seg_start = int(float(segment.get("start", 0.0)))
        seg_end = int(float(segment.get("end", 0.0)))
        prob = float(segment.get("no_speech_prob", 0.0))

        for second in range(seg_start, seg_end + 1):
            no_speech_lookup[second] = max(prob, no_speech_lookup.get(second, 0.0))

    duration = int(float(video_data.get("duration", 0.0)))
    if duration <= 0:
        all_seconds = set(motion_lookup) | set(energy_lookup) | set(silence_lookup) | set(scene_age_lookup)
        duration = max(all_seconds) if all_seconds else 0

    retention = 100.0
    retention_curve = []

    for second in range(0, duration + 1):
        motion = float(motion_lookup.get(second, 0.0))
        energy = float(energy_lookup.get(second, 0.0))
        silence = bool(silence_lookup.get(second, True))
        scene_age = float(scene_age_lookup.get(second, 0.0))

        if second in no_speech_lookup:
            no_speech_confidence = float(no_speech_lookup[second])
        else:
            no_speech_confidence = 1.0 if silence else 0.0

        silence_penalty = SILENCE_PENALTY_WEIGHT * (1.0 if silence else 0.0)

        motion_scale = 0.0
        if MOTION_LOW_THRESHOLD > 0 and motion < MOTION_LOW_THRESHOLD:
            motion_scale = (MOTION_LOW_THRESHOLD - motion) / MOTION_LOW_THRESHOLD
        low_motion_penalty = LOW_MOTION_PENALTY_WEIGHT * max(0.0, min(motion_scale, 1.0))

        long_scene_penalty = LONG_SCENE_PENALTY_WEIGHT * max(0.0, min(scene_age, 1.0))

        low_energy_threshold = 0.3
        if energy < low_energy_threshold:
            low_energy_scale = (low_energy_threshold - energy) / low_energy_threshold
        else:
            low_energy_scale = 0.0
        low_energy_penalty = LOW_MOTION_PENALTY_WEIGHT * max(0.0, min(low_energy_scale, 1.0))

        if no_speech_confidence > NO_SPEECH_PROB_THRESHOLD and NO_SPEECH_PROB_THRESHOLD < 1:
            no_speech_scale = (no_speech_confidence - NO_SPEECH_PROB_THRESHOLD) / (1.0 - NO_SPEECH_PROB_THRESHOLD)
        else:
            no_speech_scale = 0.0
        high_no_speech_penalty = SILENCE_PENALTY_WEIGHT * max(0.0, min(no_speech_scale, 1.0))

        total_penalty = (
            silence_penalty
            + low_motion_penalty
            + long_scene_penalty
            + low_energy_penalty
            + high_no_speech_penalty
        )
        total_penalty = min(total_penalty, 4.5)

        retention = max(0.0, retention - total_penalty)

        retention_curve.append(
            {
                "time": second,
                "retention": round(retention, 3),
                "signals": {
                    "motion": motion,
                    "energy": energy,
                    "silence": silence,
                    "scene_age": scene_age,
                    "no_speech_confidence": no_speech_confidence,
                },
            }
        )

    if retention_curve:
        raw_retention = np.array([point["retention"] for point in retention_curve], dtype=float)

        window = 5
        sigma = 1.5
        half = window // 2
        x = np.arange(-half, half + 1)
        kernel = np.exp(-(x ** 2) / (2 * (sigma ** 2)))
        kernel = kernel / np.sum(kernel)

        padded = np.pad(raw_retention, (half, half), mode="edge")
        smoothed = np.convolve(padded, kernel, mode="valid")

        constrained = np.copy(smoothed)
        split_index = int(len(constrained) * 0.6)

        constrained[0] = max(0.0, min(100.0, constrained[0]))

        for i in range(1, len(constrained)):
            if i < split_index:
                constrained[i] = min(constrained[i], constrained[i - 1])
            else:
                constrained[i] = min(constrained[i], constrained[i - 1] + 2.0)

            constrained[i] = max(0.0, min(100.0, constrained[i]))

        for i, point in enumerate(retention_curve):
            point["retention"] = round(float(constrained[i]), 3)

    weak_seconds = [int(p["time"]) for p in retention_curve if float(p["retention"]) < 70.0]
    weak_runs = _build_runs(weak_seconds)
    weak_runs = _merge_runs_with_small_gaps(weak_runs, max_gap=5)

    weak_segments = []
    for start, end in weak_runs:
        stats = _segment_stats(retention_curve, start, end)
        avg_retention = stats["avg_retention"]

        weak_segments.append(
            {
                "start": start,
                "end": end,
                "duration": end - start + 1,
                "avg_retention": round(avg_retention, 3),
                "dominant_signal": _dominant_signal(stats, mode="weak"),
                "severity": _weak_severity(avg_retention),
            }
        )

    strong_seconds = [int(p["time"]) for p in retention_curve if float(p["retention"]) > 80.0]
    strong_runs = _build_runs(strong_seconds)

    strong_segments = []
    for start, end in strong_runs:
        duration_seconds = end - start + 1
        if duration_seconds < 8:
            continue

        stats = _segment_stats(retention_curve, start, end)
        strong_segments.append(
            {
                "start": start,
                "end": end,
                "duration": duration_seconds,
                "avg_retention": round(stats["avg_retention"], 3),
                "dominant_signal": _dominant_signal(stats, mode="strong"),
            }
        )

    hook_points = [float(p["retention"]) for p in retention_curve if int(p["time"]) <= 15]
    hook_score = float(np.mean(hook_points)) if hook_points else 0.0

    retention_points = [float(p["retention"]) for p in retention_curve]
    retention_score = float(np.mean(retention_points)) if retention_points else 0.0

    motion_values = [float(v) for v in motion_lookup.values()]
    motion_score = float(np.mean(motion_values) * 100.0) if motion_values else 0.0
    motion_score = max(0.0, min(100.0, motion_score))

    speech_stats = audio_data.get("speech_stats", {}) if isinstance(audio_data, dict) else {}
    if "average_energy" in speech_stats:
        avg_energy = float(speech_stats.get("average_energy", 0.0))
    else:
        energy_values = [float(v) for v in energy_lookup.values()]
        avg_energy = float(np.mean(energy_values)) if energy_values else 0.0

    audio_score = max(0.0, min(100.0, avg_energy * 100.0))

    scenes = video_data.get("scenes", [])
    if scenes:
        scene_durations = [max(0.0, float(s.get("end", 0.0)) - float(s.get("start", 0.0))) for s in scenes]
        avg_scene_duration = float(np.mean(scene_durations)) if scene_durations else 0.0
        deviation = min(1.0, abs(avg_scene_duration - 5.0) / 5.0)
        long_scene_ratio = float(np.mean([1.0 if d > 10.0 else 0.0 for d in scene_durations])) if scene_durations else 0.0
        pacing_quality = max(0.0, min(1.0, 1.0 - (0.7 * deviation + 0.3 * long_scene_ratio)))
        pacing_score = pacing_quality * 100.0
    else:
        pacing_score = 50.0

    vpq_components = {
        "hook_score": round(hook_score, 3),
        "retention_score": round(retention_score, 3),
        "motion_score": round(motion_score, 3),
        "audio_score": round(audio_score, 3),
        "pacing_score": round(pacing_score, 3),
    }

    vpq_score = (
        0.25 * vpq_components["hook_score"]
        + 0.30 * vpq_components["retention_score"]
        + 0.15 * vpq_components["motion_score"]
        + 0.20 * vpq_components["audio_score"]
        + 0.10 * vpq_components["pacing_score"]
    )

    return {
        "motion_lookup": motion_lookup,
        "energy_lookup": energy_lookup,
        "silence_lookup": silence_lookup,
        "scene_age_lookup": scene_age_lookup,
        "retention_curve": retention_curve,
        "weak_segments": weak_segments,
        "strong_segments": strong_segments,
        "vpq_score": round(vpq_score, 3),
        "vpq_components": vpq_components,
    }





