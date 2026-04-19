import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)


def extract_dialogue_for_segment(start, end, transcription):
    lines = []
    for seg in transcription or []:
        seg_start = float(seg.get("start", 0.0))
        seg_end = float(seg.get("end", 0.0))
        no_speech_prob = float(seg.get("no_speech_prob", 1.0))
        if seg_start <= end and seg_end >= start and no_speech_prob < 0.4:
            text = str(seg.get("text", "")).strip()
            if text:
                lines.append(text)
    return " ".join(lines)[:200]


def generate_suggestions(retention_analysis, transcription=None, motion_data=None, *args):
    # Backward compatibility for existing pipeline call:
    # generate_suggestions(video_data, audio_data, retention_data, features)
    if (
        isinstance(motion_data, dict)
        and "vpq_score" in motion_data
        and isinstance(transcription, dict)
        and isinstance(retention_analysis, dict)
        and "weak_segments" not in retention_analysis
    ):
        video_data = retention_analysis
        audio_data = transcription
        retention_analysis = motion_data
        transcription = audio_data.get("transcription", [])
        motion_data = video_data.get("motion_scores", [])

    weak_segments = retention_analysis["weak_segments"]
    vpq_components = retention_analysis["vpq_components"]
    overall_score = retention_analysis["vpq_score"]
    metadata = retention_analysis.get("analysis_metadata", {})
    platform_profile = str(metadata.get("platform_profile", "hybrid"))

    signal_map = {
        "low_motion": ("Low visual activity", "Add B-roll or camera movement"),
        "silence": ("Extended silence", "Add narration or remove this segment"),
        "long_scene": ("Scene held too long", "Add cuts or transitions"),
        "low_energy": ("Flat vocal delivery", "Increase energy or add overlays"),
        # Compatibility with current retention signal names
        "motion": ("Low visual activity", "Add B-roll or camera movement"),
        "scene_age": ("Scene held too long", "Add cuts or transitions"),
        "energy": ("Flat vocal delivery", "Increase energy or add overlays"),
        "no_speech_confidence": ("Extended silence", "Add narration or remove this segment"),
    }
    reason_map = {
        "low_motion": "Low motion detected in this segment",
        "silence": "High silence detected (low speech activity)",
        "long_scene": "Scene duration exceeded optimal length",
        "low_energy": "Audio energy levels were consistently low",
        # Compatibility with current retention signal names
        "motion": "Low motion detected in this segment",
        "scene_age": "Scene duration exceeded optimal length",
        "energy": "Audio energy levels were consistently low",
        "no_speech_confidence": "High silence detected (low speech activity)",
    }

    suggestions = []
    for segment in weak_segments:
        start = int(segment.get("start", 0))
        end = int(segment.get("end", 0))
        dominant_signal = str(segment.get("dominant_signal", ""))
        signals = segment.get("signals", {})
        if not dominant_signal and isinstance(signals, dict) and signals:
            dominant_signal = str(max(signals, key=lambda k: float(signals.get(k, 0.0))))
        issue, fix = signal_map.get(
            dominant_signal,
            ("Retention drop detected", "Tighten pacing and add stronger visuals/audio."),
        )
        reason = reason_map.get(dominant_signal, "Retention dropped in this segment")

        _ = extract_dialogue_for_segment(start, end, transcription or [])

        suggestions.append(
            {
                "timestamp_start": start,
                "timestamp_end": end,
                "issue": issue,
                "reason": reason,
                "fix": fix,
                "priority": "High",
            }
        )

    if float(vpq_components["hook_score"]) < 70:
        suggestions.append(
            {
                "timestamp_start": 0,
                "timestamp_end": 10,
                "issue": "Weak hook",
                "reason": "The opening does not introduce a strong enough hook",
                "fix": "Move most engaging moment to first 8 seconds",
                "priority": "High",
            }
        )

    # Component-level fallback suggestions for cases with strong retention but weak sub-scores.
    if float(vpq_components.get("pacing_score", 100.0)) < 65:
        suggestions.append(
            {
                "timestamp_start": 0,
                "timestamp_end": 15,
                "issue": "Pacing is inconsistent",
                "reason": "Scene rhythm varies too much and slows viewer momentum",
                "fix": "Increase cut frequency and remove slow transitions in low-action moments.",
                "priority": "High",
            }
        )

    if float(vpq_components.get("motion_score", 100.0)) < 60:
        suggestions.append(
            {
                "timestamp_start": 0,
                "timestamp_end": 15,
                "issue": "Average motion is low",
                "reason": "Low motion detected in this segment",
                "fix": "Use more camera movement, jump cuts, or B-roll overlays to maintain visual momentum.",
                "priority": "High",
            }
        )

    if float(vpq_components.get("audio_score", 100.0)) < 60:
        suggestions.append(
            {
                "timestamp_start": 0,
                "timestamp_end": 15,
                "issue": "Audio energy is low",
                "reason": "Audio energy levels were consistently low",
                "fix": "Improve vocal projection and add audio dynamics (music dips, emphasis, cadence variation).",
                "priority": "Medium",
            }
        )

    # Platform-aware optimization hints.
    if platform_profile in ("reel", "hybrid"):
        if float(vpq_components.get("completion_score", 100.0)) < 85:
            suggestions.append(
                {
                    "timestamp_start": 0,
                    "timestamp_end": 8,
                    "issue": "Completion potential is low",
                    "reason": "Early retention behavior suggests viewers are dropping before payoff",
                    "fix": "Tighten the first 8 seconds and reduce dead space between spoken beats.",
                    "priority": "High",
                }
            )

        if float(vpq_components.get("shareability_score", 100.0)) < 75:
            suggestions.append(
                {
                    "timestamp_start": 0,
                    "timestamp_end": 12,
                    "issue": "Low shareability signal",
                    "reason": "Content currently lacks a clear high-impact or highly relatable payoff",
                    "fix": "Add a stronger payoff: surprising line, clear takeaway, or relatable punch moment.",
                    "priority": "High",
                }
            )

        if float(vpq_components.get("replay_score", 100.0)) < 82 and platform_profile == "reel":
            suggestions.append(
                {
                    "timestamp_start": 0,
                    "timestamp_end": 10,
                    "issue": "Replay potential is weak",
                    "reason": "Ending does not strongly encourage immediate rewatch behavior",
                    "fix": "Use tighter loops: end with a callback or visual continuation that encourages rewatch.",
                    "priority": "Medium",
                }
            )
    else:
        if float(vpq_components.get("retention_score", 100.0)) < 75:
            suggestions.append(
                {
                    "timestamp_start": 30,
                    "timestamp_end": 90,
                    "issue": "Mid-video retention softness",
                    "reason": "Viewer attention tapers in the middle section without enough pattern interrupts",
                    "fix": "Introduce pattern interrupts every 20–40 seconds (new angle, proof, demo, or story beat).",
                    "priority": "High",
                }
            )

    sorted_components = sorted(vpq_components.items(), key=lambda item: item[1])
    if len(sorted_components) >= 2:
        key1 = sorted_components[0][0]
        key2 = sorted_components[1][0]
    elif len(sorted_components) == 1:
        key1 = sorted_components[0][0]
        key2 = sorted_components[0][0]
    else:
        key1 = "hook_score"
        key2 = "retention_score"
    summary = f"This video scores {overall_score}/100. Improve {key1} and {key2}."

    # Keep rule-based output as fallback; replace with LLM output when valid.
    fallback_summary = summary
    fallback_suggestions = suggestions

    system_prompt = (
        "You are a YouTube content strategist. Respond ONLY in valid JSON. "
        "No markdown, no explanation."
    )
    user_prompt = (
        f"VPQ score: {overall_score}\n"
        f"Weak segments (start, end, dominant_signal): "
        f"{[{ 'start': int(s.get('start', 0)), 'end': int(s.get('end', 0)), 'dominant_signal': s.get('dominant_signal', '') } for s in weak_segments]}\n"
        f"Strong segments: {retention_analysis.get('strong_segments', [])}\n\n"
        "Rules:\n"
        "- Return ONLY valid JSON.\n"
        "- Provide 1 to 5 suggestions based on actual issues; do not invent unnecessary suggestions.\n"
        "- Use only priority values: High, Medium, Low.\n"
        "- Every suggestion MUST include a non-empty reason field.\n"
        "- Keep fixes specific and actionable.\n\n"
        "Return JSON in this format:\n"
        "{\n"
        '  "summary": "...",\n'
        '  "suggestions": [\n'
        "    {\n"
        '      "timestamp_start": int,\n'
        '      "timestamp_end": int,\n'
        '      "issue": "...",\n'
        '      "reason": "...",\n'
        '      "fix": "...",\n'
        '      "priority": "High/Medium/Low"\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=1500,
        )

        content = response.choices[0].message.content or ""
        content = content.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(content)

        if "suggestions" not in parsed:
            raise ValueError("Missing suggestions key in Groq response")

        summary = str(parsed.get("summary", fallback_summary))
        suggestions = parsed["suggestions"]
    except Exception:
        summary = fallback_summary
        suggestions = fallback_suggestions

    if overall_score >= 90:
        grade = "A"
    elif overall_score >= 80:
        grade = "B"
    elif overall_score >= 70:
        grade = "C"
    elif overall_score >= 60:
        grade = "D"
    else:
        grade = "F"

    retention_curve_raw = retention_analysis.get("retention_curve", []) if isinstance(retention_analysis, dict) else []
    retention_curve = []
    for point in retention_curve_raw:
        retention_curve.append(
            {
                "time": int(point.get("time", 0)),
                "retention": float(point.get("retention", 0.0)),
            }
        )

    weak_segments_raw = weak_segments if isinstance(weak_segments, list) else []
    weak_segments_out = []
    for segment in weak_segments_raw:
        start = int(segment.get("start", 0))
        end = int(segment.get("end", start))
        weak_segments_out.append(
            {
                "start": start,
                "end": end,
                "duration": int(segment.get("duration", max(0, end - start + 1))),
                "avg_retention": float(segment.get("avg_retention", 0.0)),
                "dominant_signal": str(segment.get("dominant_signal", "")),
            }
        )

    strong_segments_raw = retention_analysis.get("strong_segments", []) if isinstance(retention_analysis, dict) else []
    strong_segments_out = []
    for segment in strong_segments_raw:
        start = int(segment.get("start", 0))
        end = int(segment.get("end", start))
        strong_segments_out.append(
            {
                "start": start,
                "end": end,
                "duration": int(segment.get("duration", max(0, end - start + 1))),
                "avg_retention": float(segment.get("avg_retention", 0.0)),
            }
        )

    suggestions_raw = suggestions if isinstance(suggestions, list) else []
    suggestions_out = []
    for item in suggestions_raw:
        issue_text = str(item.get("issue", ""))
        reason_text = str(item.get("reason", "")).strip()
        if not reason_text:
            reason_text = "This segment shows signs of retention weakness"
        suggestions_out.append(
            {
                "timestamp_start": int(item.get("timestamp_start", 0)),
                "timestamp_end": int(item.get("timestamp_end", 0)),
                "issue": issue_text,
                "reason": reason_text,
                "fix": str(item.get("fix", "")),
                "priority": str(item.get("priority", "Medium")),
            }
        )

    vpq_components_out = {
        "hook_score": float(vpq_components.get("hook_score", 0.0)),
        "retention_score": float(vpq_components.get("retention_score", 0.0)),
        "motion_score": float(vpq_components.get("motion_score", 0.0)),
        "audio_score": float(vpq_components.get("audio_score", 0.0)),
        "pacing_score": float(vpq_components.get("pacing_score", 0.0)),
    }

    metadata_out = retention_analysis.get("analysis_metadata", {}) if isinstance(retention_analysis, dict) else {}
    analysis_metadata_out = {
        "total_duration": int(float(metadata_out.get("total_duration", 0))),
        "weak_segment_count": int(metadata_out.get("weak_segment_count", len(weak_segments_out))),
        "strong_segment_count": int(metadata_out.get("strong_segment_count", len(strong_segments_out))),
    }

    return {
        "overall_score": int(overall_score),
        "grade": str(grade),
        "summary": str(summary),
        "retention_curve": retention_curve,
        "weak_segments": weak_segments_out,
        "strong_segments": strong_segments_out,
        "suggestions": suggestions_out,
        "vpq_components": vpq_components_out,
        "analysis_metadata": analysis_metadata_out,
    }
