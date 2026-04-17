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

    suggestions = []
    for segment in weak_segments:
        start = int(segment.get("start", 0))
        end = int(segment.get("end", 0))
        dominant_signal = str(segment.get("dominant_signal", ""))
        issue, fix = signal_map.get(
            dominant_signal,
            ("Retention drop detected", "Tighten pacing and add stronger visuals/audio."),
        )

        _ = extract_dialogue_for_segment(start, end, transcription or [])

        suggestions.append(
            {
                "timestamp_start": start,
                "timestamp_end": end,
                "issue": issue,
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
        "- Keep fixes specific and actionable.\n\n"
        "Return JSON in this format:\n"
        "{\n"
        '  "summary": "...",\n'
        '  "suggestions": [\n'
        "    {\n"
        '      "timestamp_start": int,\n'
        '      "timestamp_end": int,\n'
        '      "issue": "...",\n'
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

    return {
        "overall_score": overall_score,
        "grade": grade,
        "summary": summary,
        "suggestions": suggestions,
        "vpq_components": vpq_components,
        "strong_segments": retention_analysis["strong_segments"],
        "retention_curve": retention_analysis["retention_curve"],
        "weak_segments": weak_segments,
        "motion_data": motion_data,
        "analysis_metadata": retention_analysis["analysis_metadata"],
    }
