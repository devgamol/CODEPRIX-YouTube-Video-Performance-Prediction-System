import os

try:
    from moviepy import VideoFileClip
except ImportError:
    from moviepy.editor import VideoFileClip

import librosa
import numpy as np
import whisper

from config import NO_SPEECH_PROB_THRESHOLD, WHISPER_MODEL

whisper_model = whisper.load_model(WHISPER_MODEL)


def analyze_audio(video_path: str, job_id: str) -> dict:
    try:
        output_dir = os.path.join("uploads", job_id)
        os.makedirs(output_dir, exist_ok=True)

        audio_path = os.path.join(output_dir, "audio.wav")

        clip = VideoFileClip(video_path)
        if clip.audio is None:
            clip.close()
            return {"transcription": [], "energy_curve": [], "silence_map": {}, "speech_stats": {}}

        clip.audio.write_audiofile(
            audio_path,
            fps=16000,
            nbytes=2,
            codec="pcm_s16le",
            ffmpeg_params=["-ac", "1"],
            logger=None,
        )
        clip.close()

        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        audio_duration = float(librosa.get_duration(y=y, sr=sr))

        rms = librosa.feature.rms(y=y)[0]
        frame_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)

        per_second = {}
        for i, value in enumerate(rms):
            second = int(frame_times[i])
            per_second.setdefault(second, []).append(float(value))

        raw_curve = []
        for second in sorted(per_second.keys()):
            avg_energy = float(np.mean(per_second[second]))
            raw_curve.append({"timestamp": float(second), "energy": avg_energy})

        max_energy = max((item["energy"] for item in raw_curve), default=0.0)
        if max_energy > 0:
            energy_curve = [
                {"timestamp": item["timestamp"], "energy": item["energy"] / max_energy}
                for item in raw_curve
            ]
        else:
            energy_curve = [
                {"timestamp": item["timestamp"], "energy": 0.0}
                for item in raw_curve
            ]

        energy_map = {int(item["timestamp"]): float(item["energy"]) for item in energy_curve}

        result = whisper_model.transcribe(audio_path)

        raw_segments = result.get("segments", [])

        transcription = []
        for segment in raw_segments:
            start = float(segment.get("start", 0.0))
            end = float(segment.get("end", 0.0))
            text = str(segment.get("text", "")).strip()
            no_speech_prob = float(segment.get("no_speech_prob", 0.0))
            duration = end - start

            if not text:
                continue
            if duration < 0.3:
                continue
            if no_speech_prob > NO_SPEECH_PROB_THRESHOLD:
                continue

            start_sec = int(start)
            end_sec = int(end)
            second_values = [energy_map[s] for s in range(start_sec, end_sec + 1) if s in energy_map]
            if second_values:
                energy_level = float(np.mean(second_values))
            else:
                energy_level = 0.0

            transcription.append(
                {
                    "start": start,
                    "end": end,
                    "text": text,
                    "no_speech_prob": no_speech_prob,
                    "energy_level": energy_level,
                }
            )

        silence_map = {}
        max_second = int(np.floor(audio_duration))
        for second in range(max_second + 1):
            overlapping = []
            second_start = float(second)
            second_end = float(second + 1)

            for segment in raw_segments:
                seg_start = float(segment.get("start", 0.0))
                seg_end = float(segment.get("end", 0.0))
                if seg_end > second_start and seg_start < second_end:
                    overlapping.append(segment)

            energy_value = float(energy_map.get(second, 0.0))

            if not overlapping:
                is_silence = True
            else:
                has_speech_like_segment = any(
                    float(seg.get("no_speech_prob", 0.0)) <= NO_SPEECH_PROB_THRESHOLD
                    for seg in overlapping
                )
                is_silence = (not has_speech_like_segment) or (energy_value < 0.1)

            silence_map[str(second)] = is_silence

        non_silent_energies = [item["energy"] for item in energy_curve if not silence_map.get(str(int(item["timestamp"])), True)]

        total_silence_seconds = sum(1 for v in silence_map.values() if v)
        total_speech_seconds = len(silence_map) - total_silence_seconds

        if non_silent_energies:
            average_energy = float(np.mean(non_silent_energies))
            energy_variance = float(np.var(non_silent_energies))
        else:
            average_energy = 0.0
            energy_variance = 0.0

        speech_stats = {
            "total_speech_seconds": total_speech_seconds,
            "total_silence_seconds": total_silence_seconds,
            "average_energy": average_energy,
            "energy_variance": energy_variance,
            "flat_delivery_detected": energy_variance < 0.03,
        }

        return {
            "transcription": transcription,
            "energy_curve": energy_curve,
            "silence_map": silence_map,
            "speech_stats": speech_stats,
        }
    except Exception:
        return {"transcription": [], "energy_curve": [], "silence_map": {}, "speech_stats": {}}

