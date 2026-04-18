import os
import json

import cv2
import numpy as np

from config import SAMPLE_FRAME_RATE, SCENE_CHANGE_THRESHOLD


def analyze_video(video_path: str, job_id: str) -> dict:
    keyframes_dir = f"uploads/{job_id}/keyframes/"
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise Exception(f"Could not open video: {video_path} (resolved: {os.path.abspath(video_path)})")

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = round(total_frames / fps, 2) if fps > 0 else 0.0

    scenes = []
    if fps > 0 and total_frames > 0:
        ok, first_frame = capture.read()
        if ok:
            scene_starts = [0]
            boundary_scores = []

            prev_gray = cv2.cvtColor(first_frame, cv2.COLOR_BGR2GRAY)
            frame_index = 1

            while True:
                ok, frame = capture.read()
                if not ok:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                diff = cv2.absdiff(gray, prev_gray)
                cut_score = float(diff.mean())

                if cut_score > SCENE_CHANGE_THRESHOLD:
                    scene_starts.append(frame_index)
                    boundary_scores.append(cut_score)

                prev_gray = gray
                frame_index += 1

            frame_ranges = []
            for i, start_frame in enumerate(scene_starts):
                if i + 1 < len(scene_starts):
                    end_frame = scene_starts[i + 1] - 1
                else:
                    end_frame = total_frames - 1

                score = boundary_scores[i] if i < len(boundary_scores) else 0.0
                frame_ranges.append(
                    {
                        "start_frame": start_frame,
                        "end_frame": end_frame,
                        "cut_score": score,
                    }
                )

            merged_ranges = []
            for scene in frame_ranges:
                scene_seconds = (scene["end_frame"] - scene["start_frame"] + 1) / fps
                if scene_seconds < 1.0 and merged_ranges:
                    merged_ranges[-1]["end_frame"] = scene["end_frame"]
                    merged_ranges[-1]["cut_score"] = scene["cut_score"]
                else:
                    merged_ranges.append(scene)

            # Merge ultra-short opening scene into next scene to avoid noisy 0.xs first cuts.
            if len(merged_ranges) > 1:
                first_scene = merged_ranges[0]
                first_seconds = (first_scene["end_frame"] - first_scene["start_frame"] + 1) / fps
                if first_seconds < 1.0:
                    merged_ranges[1]["start_frame"] = first_scene["start_frame"]
                    merged_ranges.pop(0)

            if not merged_ranges:
                merged_ranges = [
                    {
                        "start_frame": 0,
                        "end_frame": total_frames - 1,
                        "cut_score": 0.0,
                    }
                ]

            keyframe_dir = os.path.join("uploads", job_id, "keyframes")
            os.makedirs(keyframe_dir, exist_ok=True)

            capture.release()
            keyframe_capture = cv2.VideoCapture(video_path)
            if not keyframe_capture.isOpened():
                raise Exception(f"Could not open video for keyframes: {video_path}")

            for i, scene in enumerate(merged_ranges):
                middle_frame = (scene["start_frame"] + scene["end_frame"]) // 2
                rel_keyframe_path = f"uploads/{job_id}/keyframes/scene_{i}.jpg"
                abs_keyframe_path = os.path.join("uploads", job_id, "keyframes", f"scene_{i}.jpg")

                keyframe_capture.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
                ok, frame = keyframe_capture.read()
                if ok:
                    cv2.imwrite(abs_keyframe_path, frame)

                start_sec = round(scene["start_frame"] / fps, 2)
                if i == len(merged_ranges) - 1:
                    end_sec = duration
                else:
                    end_sec = round((scene["end_frame"] + 1) / fps, 2)

                scene_duration = round(end_sec - start_sec, 2)

                scenes.append(
                    {
                        "index": i,
                        "start": start_sec,
                        "end": end_sec,
                        "duration": scene_duration,
                        "cut_score": float(scene["cut_score"]),
                        "keyframe_path": rel_keyframe_path,
                    }
                )

            keyframe_capture.release()
        else:
            capture.release()
    else:
        capture.release()

    if not scenes and duration > 0 and total_frames > 0 and fps > 0:
        keyframe_dir = os.path.join("uploads", job_id, "keyframes")
        os.makedirs(keyframe_dir, exist_ok=True)

        keyframe_path = f"uploads/{job_id}/keyframes/scene_0.jpg"
        scenes = [
            {
                "index": 0,
                "start": 0.0,
                "end": duration,
                "duration": duration,
                "cut_score": 0.0,
                "keyframe_path": keyframe_path,
            }
        ]

    motion_scores = []
    if fps > 0 and total_frames > 1:
        sample_step = max(1, int(SAMPLE_FRAME_RATE))
        motion_capture = cv2.VideoCapture(video_path)
        if not motion_capture.isOpened():
            raise Exception(f"Could not open video for motion analysis: {video_path}")

        sampled_prev_gray = None
        frame_index = 0

        while True:
            ok, frame = motion_capture.read()
            if not ok:
                break

            if frame_index % sample_step != 0:
                frame_index += 1
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if sampled_prev_gray is None:
                sampled_prev_gray = gray
                frame_index += 1
                continue

            flow = cv2.calcOpticalFlowFarneback(
                sampled_prev_gray,
                gray,
                None,
                0.5,
                3,
                15,
                3,
                5,
                1.2,
                0,
            )
            magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            motion_intensity = float(magnitude.mean())

            motion_scores.append(
                {
                    "timestamp": round(frame_index / fps, 2),
                    "motion_intensity": motion_intensity,
                }
            )

            sampled_prev_gray = gray
            frame_index += 1

        motion_capture.release()

        if motion_scores:
            raw_values = np.array([item["motion_intensity"] for item in motion_scores], dtype=float)
            padded = np.pad(raw_values, (1, 1), mode="edge")
            kernel = np.ones(3, dtype=float) / 3.0
            smoothed = np.convolve(padded, kernel, mode="valid")

            for i, item in enumerate(motion_scores):
                item["motion_intensity"] = float(smoothed[i])

            max_motion = max(item["motion_intensity"] for item in motion_scores)
            if max_motion > 0:
                for item in motion_scores:
                    item["motion_intensity"] = item["motion_intensity"] / max_motion
            else:
                for item in motion_scores:
                    item["motion_intensity"] = 0.0

    return {
        "duration": duration,
        "fps": fps,
        "total_frames": total_frames,
        "scenes": scenes,
        "motion_scores": motion_scores,
        "keyframes_dir": keyframes_dir,
    }
if __name__ == "__main__":
    candidate_paths = ["Train_reel.mp4", "Train_reel .mp4"]
    sample_video_path = next((p for p in candidate_paths if os.path.exists(p)), candidate_paths[0])
    result = analyze_video(sample_video_path, "test_job")
    print(json.dumps(result, indent=2))
