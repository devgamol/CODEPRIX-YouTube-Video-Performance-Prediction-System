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

    seconds = sorted(seconds)
    runs = []
    start = seconds[0]
    prev = seconds[0]

    for sec in seconds[1:]:
        if sec == prev + 1:
            prev = sec
            continue
        runs.append((start, prev))
        start = sec
        prev = sec

    runs.append((start, prev))
    return runs


def _merge_runs_with_small_gaps(runs, gap_limit):
    if not runs:
        return []

    merged = [runs[0]]
    for start, end in runs[1:]:
        last_start, last_end = merged[-1]
        gap = start - last_end - 1
        if gap < gap_limit:
            merged[-1] = (last_start, end)
        else:
            merged.append((start, end))

    return merged


def _interpolate_motion(duration, motion_scores):
    known = {}
    for item in motion_scores:
        sec = int(float(item.get("timestamp", 0.0)))
        if 0 <= sec <= duration:
            known[sec] = float(item.get("motion_intensity", 0.0))

    if duration < 0:
        return {}

    if not known:
        return {sec: 0.0 for sec in range(duration + 1)}

    xs = sorted(known.keys())
    ys = [known[x] for x in xs]

    full_x = np.arange(0, duration + 1, dtype=float)
    interp = np.interp(full_x, np.array(xs, dtype=float), np.array(ys, dtype=float))
    return {sec: float(interp[sec]) for sec in range(duration + 1)}


def _segment_points(retention_curve, start, end):
    return [p for p in retention_curve if start <= int(p["time"]) <= end]


def _dominant_signal(points, mode):
    if not points:
        return "silence"

    avg_motion = float(np.mean([p["signals"]["motion"] for p in points]))
    avg_energy = float(np.mean([p["signals"]["energy"] for p in points]))
    avg_silence = float(np.mean([1.0 if p["signals"]["silence"] else 0.0 for p in points]))
    avg_scene_age = float(np.mean([p["signals"]["scene_age"] for p in points]))
    avg_no_speech = float(np.mean([p["signals"]["no_speech_confidence"] for p in points]))

    if mode == "weak":
        motion_risk = 0.0
        if MOTION_LOW_THRESHOLD > 0:
            motion_risk = max(0.0, (MOTION_LOW_THRESHOLD - avg_motion) / MOTION_LOW_THRESHOLD)

        energy_risk = max(0.0, (0.25 - avg_energy) / 0.25)
        scene_age_risk = max(0.0, min(1.0, (avg_scene_age - 0.5) / 0.5))

        if NO_SPEECH_PROB_THRESHOLD < 1.0:
            no_speech_risk = max(0.0, (avg_no_speech - NO_SPEECH_PROB_THRESHOLD) / (1.0 - NO_SPEECH_PROB_THRESHOLD))
        else:
            no_speech_risk = 0.0

        scores = {
            "motion": motion_risk,
            "energy": energy_risk,
            "silence": avg_silence,
            "scene_age": scene_age_risk,
            "no_speech_confidence": no_speech_risk,
        }
    else:
        scores = {
            "motion": max(0.0, min(1.0, avg_motion)) * 1.2,
            "energy": max(0.0, min(1.0, avg_energy)) * 1.2,
            "silence": max(0.0, min(1.0, 1.0 - avg_silence)) * 0.6,
            "scene_age": max(0.0, min(1.0, 1.0 - avg_scene_age)) * 0.4,
            "no_speech_confidence": max(0.0, min(1.0, 1.0 - avg_no_speech)) * 0.6,
        }

    return max(scores, key=scores.get)


def _apply_gaussian_smoothing(retention_curve):
    if not retention_curve:
        return retention_curve

    values = np.array([float(p["retention"]) for p in retention_curve], dtype=float)

    window = 5
    sigma = 1.5
    half = window // 2
    x = np.arange(-half, half + 1)
    kernel = np.exp(-(x ** 2) / (2 * sigma * sigma))
    kernel = kernel / np.sum(kernel)

    padded = np.pad(values, (half, half), mode="edge")
    smoothed = np.convolve(padded, kernel, mode="valid")

    constrained = np.copy(smoothed)
    split = int(len(constrained) * 0.6)

    constrained[0] = max(0.0, min(100.0, constrained[0]))
    for i in range(1, len(constrained)):
        if i < split:
            constrained[i] = min(constrained[i], constrained[i - 1])
        else:
            constrained[i] = min(constrained[i], constrained[i - 1] + 2.0)
        constrained[i] = max(0.0, min(100.0, constrained[i]))

    for i, p in enumerate(retention_curve):
        p["retention"] = round(float(constrained[i]), 3)

    return retention_curve


def compute_retention_analysis(video_data, audio_data, features=None):
    total_duration = float(video_data.get("duration", 0.0))
    duration = int(total_duration)
    if duration < 0:
        duration = 0

    motion_lookup = _interpolate_motion(duration, video_data.get("motion_scores", []))

    energy_sparse = {}
    for item in audio_data.get("energy_curve", []):
        sec = int(float(item.get("timestamp", 0.0)))
        if 0 <= sec <= duration:
            energy_sparse[sec] = float(item.get("energy", 0.0))
    energy_lookup = {sec: float(energy_sparse.get(sec, 0.0)) for sec in range(duration + 1)}

    silence_sparse = {}
    for k, v in audio_data.get("silence_map", {}).items():
        sec = int(k)
        if 0 <= sec <= duration:
            silence_sparse[sec] = bool(v)
    silence_lookup = {sec: bool(silence_sparse.get(sec, False)) for sec in range(duration + 1)}

    scene_start_lookup = {}
    for scene in video_data.get("scenes", []):
        start = int(float(scene.get("start", 0.0)))
        end = int(float(scene.get("end", 0.0)))
        for sec in range(max(0, start), min(duration, end) + 1):
            scene_start_lookup[sec] = start

    scene_age_lookup = {}
    for sec in range(duration + 1):
        if sec in scene_start_lookup:
            age = (sec - scene_start_lookup[sec]) / 45.0
            scene_age_lookup[sec] = max(0.0, min(age, 1.0))
        else:
            scene_age_lookup[sec] = 0.0

    no_speech_lookup = {sec: 0.0 for sec in range(duration + 1)}
    for segment in audio_data.get("transcription", []):
        seg_start = int(float(segment.get("start", 0.0)))
        seg_end = int(float(segment.get("end", 0.0)))
        prob = float(segment.get("no_speech_prob", 0.0))
        for sec in range(max(0, seg_start), min(duration, seg_end) + 1):
            no_speech_lookup[sec] = max(no_speech_lookup[sec], prob)

    clip_scene = {}
    face_scene = {}
    if isinstance(features, dict):
        for item in features.get("clip_scores", []):
            scene_idx = int(item.get("scene_index", -1))
            clip_scene[scene_idx] = float(item.get("clip_score", 0.5))

        for item in features.get("face_data", []):
            scene_idx = int(item.get("scene_index", -1))
            face_scene[scene_idx] = bool(item.get("face_detected", False))

    clip_lookup = {sec: 0.5 for sec in range(duration + 1)}
    face_lookup = {sec: False for sec in range(duration + 1)}

    for idx, scene in enumerate(video_data.get("scenes", [])):
        scene_idx = int(scene.get("index", idx))
        start = int(float(scene.get("start", 0.0)))
        end = int(float(scene.get("end", 0.0)))

        clip_val = float(clip_scene.get(scene_idx, 0.5))
        face_val = bool(face_scene.get(scene_idx, False))

        for sec in range(max(0, start), min(duration, end) + 1):
            clip_lookup[sec] = clip_val
            face_lookup[sec] = face_val

    retention = 100.0
    retention_curve = []
    prev_silent = False

    for sec in range(duration + 1):
        motion = float(motion_lookup[sec])
        energy = float(energy_lookup[sec])
        silence = bool(silence_lookup[sec])
        scene_age = float(scene_age_lookup[sec])
        no_speech_confidence = float(no_speech_lookup[sec])

        silence_penalty = 0.0
        if silence:
            silence_penalty = SILENCE_PENALTY_WEIGHT
            if prev_silent:
                silence_penalty += SILENCE_PENALTY_WEIGHT * 0.5

        if MOTION_LOW_THRESHOLD > 0 and motion < MOTION_LOW_THRESHOLD:
            motion_scale = (MOTION_LOW_THRESHOLD - motion) / MOTION_LOW_THRESHOLD
            low_motion_penalty = LOW_MOTION_PENALTY_WEIGHT * max(0.0, min(motion_scale, 1.0))
        else:
            low_motion_penalty = 0.0

        if scene_age > 0.5:
            long_scene_scale = (scene_age - 0.5) / 0.5
            long_scene_penalty = LONG_SCENE_PENALTY_WEIGHT * max(0.0, min(long_scene_scale, 1.0))
        else:
            long_scene_penalty = 0.0

        if energy < 0.25:
            low_energy_scale = (0.25 - energy) / 0.25
            low_energy_penalty = LOW_MOTION_PENALTY_WEIGHT * max(0.0, min(low_energy_scale, 1.0))
        else:
            low_energy_penalty = 0.0

        if no_speech_confidence > NO_SPEECH_PROB_THRESHOLD and NO_SPEECH_PROB_THRESHOLD < 1.0:
            no_speech_scale = (no_speech_confidence - NO_SPEECH_PROB_THRESHOLD) / (1.0 - NO_SPEECH_PROB_THRESHOLD)
            high_no_speech_penalty = SILENCE_PENALTY_WEIGHT * max(0.0, min(no_speech_scale, 1.0))
        else:
            high_no_speech_penalty = 0.0

        clip_penalty = 0.0
        clip_boost = 0.0
        clip_score = float(clip_lookup.get(sec, 0.5))
        if clip_score < 0.35:
            clip_penalty = 0.6 * ((0.35 - clip_score) / 0.35)
        elif clip_score > 0.75:
            clip_boost = 0.3 * ((clip_score - 0.75) / 0.25)

        face_boost = 0.15 if face_lookup.get(sec, False) else 0.0

        total_penalty = (
            silence_penalty
            + low_motion_penalty
            + long_scene_penalty
            + low_energy_penalty
            + high_no_speech_penalty
            + clip_penalty
            - clip_boost
            - face_boost
        )
        total_penalty = max(0.0, min(total_penalty, 4.5))

        retention = max(0.0, retention - total_penalty)

        retention_curve.append(
            {
                "time": sec,
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

        prev_silent = silence

    retention_curve = _apply_gaussian_smoothing(retention_curve)

    weak_seconds = [int(p["time"]) for p in retention_curve if float(p["retention"]) < 70.0]
    weak_runs = _merge_runs_with_small_gaps(_build_runs(weak_seconds), gap_limit=5)

    weak_segments = []
    for start, end in weak_runs:
        points = _segment_points(retention_curve, start, end)
        if not points:
            continue

        avg_ret = float(np.mean([p["retention"] for p in points]))
        if avg_ret < 55.0:
            severity = "critical"
        elif avg_ret < 65.0:
            severity = "severe"
        else:
            severity = "moderate"

        weak_segments.append(
            {
                "start": start,
                "end": end,
                "duration": end - start + 1,
                "avg_retention": round(avg_ret, 3),
                "dominant_signal": _dominant_signal(points, mode="weak"),
                "severity": severity,
            }
        )

    strong_seconds = [int(p["time"]) for p in retention_curve if float(p["retention"]) > 80.0]
    strong_runs = _build_runs(strong_seconds)

    strong_segments = []
    for start, end in strong_runs:
        dur = end - start + 1
        if dur < 8:
            continue

        points = _segment_points(retention_curve, start, end)
        if not points:
            continue

        avg_ret = float(np.mean([p["retention"] for p in points]))
        strong_segments.append(
            {
                "start": start,
                "end": end,
                "duration": dur,
                "avg_retention": round(avg_ret, 3),
                "dominant_signal": _dominant_signal(points, mode="strong"),
            }
        )

    retention_values = [float(p["retention"]) for p in retention_curve]
    hook_values = [float(p["retention"]) for p in retention_curve if int(p["time"]) <= 15]

    hook_score = float(np.mean(hook_values)) if hook_values else 0.0

    if len(retention_values) > 1:
        auc = float(np.trapezoid(np.array(retention_values, dtype=float), dx=1.0))
        max_auc = 100.0 * float(len(retention_values) - 1)
        retention_score = (auc / max_auc) * 100.0 if max_auc > 0 else 0.0
    elif retention_values:
        retention_score = retention_values[0]
    else:
        retention_score = 0.0

    motion_score = float(np.mean(list(motion_lookup.values())) * 100.0) if motion_lookup else 0.0
    audio_score = float(np.mean(list(energy_lookup.values())) * 100.0) if energy_lookup else 0.0

    scenes = video_data.get("scenes", [])
    cuts = max(0, len(scenes) - 1)
    minutes = total_duration / 60.0 if total_duration > 0 else 0.0
    cuts_per_min = float(cuts / minutes) if minutes > 0 else 0.0
    pacing_score = max(0.0, 100.0 - (abs(cuts_per_min - 5.0) / 5.0) * 100.0)

    vpq_components = {
        "hook_score": round(max(0.0, min(100.0, hook_score)), 3),
        "retention_score": round(max(0.0, min(100.0, retention_score)), 3),
        "motion_score": round(max(0.0, min(100.0, motion_score)), 3),
        "audio_score": round(max(0.0, min(100.0, audio_score)), 3),
        "pacing_score": round(max(0.0, min(100.0, pacing_score)), 3),
    }

    vpq_raw = (
        0.25 * vpq_components["hook_score"]
        + 0.30 * vpq_components["retention_score"]
        + 0.15 * vpq_components["motion_score"]
        + 0.20 * vpq_components["audio_score"]
        + 0.10 * vpq_components["pacing_score"]
    )
    vpq_score = int(round(max(0.0, min(100.0, vpq_raw))))

    speech_stats = audio_data.get("speech_stats", {}) if isinstance(audio_data, dict) else {}
    if "flat_delivery_detected" in speech_stats:
        flat_delivery_detected = bool(speech_stats.get("flat_delivery_detected"))
    else:
        energy_var = float(np.var(list(energy_lookup.values()))) if energy_lookup else 0.0
        flat_delivery_detected = energy_var < 0.03

    face_data = features.get("face_data", []) if isinstance(features, dict) else []
    if face_data:
        face_scene_ratio = float(np.mean([1.0 if item.get("face_detected") else 0.0 for item in face_data]))
        presenter_heavy = face_scene_ratio > 0.6
    else:
        presenter_heavy = False

    analysis_metadata = {
        "total_duration": total_duration,
        "total_seconds_analyzed": len(retention_curve),
        "weak_segment_count": len(weak_segments),
        "strong_segment_count": len(strong_segments),
        "predicted_average_retention": round(float(np.mean(retention_values)) if retention_values else 0.0, 3),
        "flat_delivery_detected": flat_delivery_detected,
        "presenter_heavy": presenter_heavy,
    }

    signal_weights = {
        "silence_penalty": SILENCE_PENALTY_WEIGHT,
        "low_motion_penalty": LOW_MOTION_PENALTY_WEIGHT,
        "long_scene_penalty": LONG_SCENE_PENALTY_WEIGHT,
        "low_energy_penalty": LOW_MOTION_PENALTY_WEIGHT,
        "high_no_speech_penalty": SILENCE_PENALTY_WEIGHT,
    }

    return {
        "retention_curve": retention_curve,
        "weak_segments": weak_segments,
        "strong_segments": strong_segments,
        "vpq_score": vpq_score,
        "vpq_components": vpq_components,
        "signal_weights": signal_weights,
        "analysis_metadata": analysis_metadata,
    }
