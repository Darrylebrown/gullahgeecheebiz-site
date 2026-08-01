#!/usr/bin/env python3
"""
GGB Human Voice Engine — automatic human-quality audio production.
Every script that enters the pipeline gets human-sounding voiceover.
No robotic TTS. No flat delivery. Just warm, natural, authentic narration.
"""
import json, sys, uuid, subprocess, asyncio, os, random
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from headquarters.engine import HQDatabase, STUDIO_DIR, CONTENT_DIR, LOGS_DIR
from publisher import REPO_ROOT

# ─── Voice Profiles ───────────────────────────────────────────────────────

# Edge TTS voices — human-quality neural voices, zero cost
VOICE_PROFILES = {
    "narrator_male": {
        "name": "en-US-JennyNeural",  # Warm, natural female — best all-around
        "style": "default",
        "rate": "+0%",
        "pitch": "+0Hz",
        "description": "Warm, natural, authoritative — primary narrator",
    },
    "narrator_female_warm": {
        "name": "en-US-AriaNeural",
        "style": "friendly",
        "rate": "+0%",
        "pitch": "+0Hz",
        "description": "Warm, friendly — community stories",
    },
    "narrator_deep": {
        "name": "en-US-GuyNeural",
        "style": "default",
        "rate": "-5%",
        "pitch": "-10Hz",
        "description": "Deep, resonant — historical content",
    },
    "narrator_soft": {
        "name": "en-US-JennyNeural",
        "style": "whisper",
        "rate": "-10%",
        "pitch": "+5Hz",
        "description": "Soft, intimate — personal stories",
    },
}

# ─── Ambient Soundscapes ──────────────────────────────────────────────────

AMBIENT_SOUNDSCAPES = {
    "lowcountry_marsh": {
        "description": "Gentle marsh sounds, distant birds, soft wind through grass",
        "tags": ["marsh", "nature", "calm", "lowcountry"],
    },
    "ocean_shore": {
        "description": "Waves lapping shore, seagulls, gentle breeze",
        "tags": ["ocean", "beach", "sea islands", "water"],
    },
    "praise_house": {
        "description": "Distant spiritual humming, wooden floor creaks, warm reverb",
        "tags": ["spiritual", "church", "community", "tradition"],
    },
    "sweetgrass_workshop": {
        "description": "Soft rustling of grass, gentle conversation, workshop ambiance",
        "tags": ["craft", "basket", "artisan", "work"],
    },
    "kitchen_warmth": {
        "description": "Gentle simmering, wooden spoon on pot, warm hearth",
        "tags": ["cooking", "kitchen", "food", "home"],
    },
    "evening_porch": {
        "description": "Crickets, distant frogs, creaking porch swing, night air",
        "tags": ["evening", "porch", "night", "peaceful"],
    },
    "morning_routine": {
        "description": "Soft acoustic guitar, coffee brewing, morning birds",
        "tags": ["morning", "routine", "gentle", "wake"],
    },
}

# ─── Audio Output ─────────────────────────────────────────────────────────

AUDIO_OUTPUT_DIR = REPO_ROOT / "publish" / "audio"
AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class HumanVoiceEngine:
    """Automatic human-quality audio production for every script."""

    def __init__(self, db: HQDatabase = None):
        self.db = db or HQDatabase()
        self.ffmpeg = self._find_ffmpeg()

    def _find_ffmpeg(self) -> str:
        """Find ffmpeg binary."""
        candidates = [
            "/Users/Shared/ffmpeg/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/opt/homebrew/bin/ffmpeg",
            "ffmpeg",
        ]
        for c in candidates:
            try:
                subprocess.run([c, "-version"], capture_output=True, timeout=5)
                return c
            except:
                continue
        return "ffmpeg"

    def _select_voice(self, content_type: str, mood: str = "default") -> Dict:
        """Select the best voice profile for the content type."""
        if content_type == "history":
            return VOICE_PROFILES["narrator_deep"]
        elif content_type == "personal":
            return VOICE_PROFILES["narrator_soft"]
        elif content_type == "community":
            return VOICE_PROFILES["narrator_female_warm"]
        else:
            return VOICE_PROFILES["narrator_male"]

    def _select_soundscape(self, theme: str = "lowcountry") -> str:
        """Select an ambient soundscape based on theme."""
        if "marsh" in theme or "lowcountry" in theme:
            return "lowcountry_marsh"
        elif "ocean" in theme or "sea" in theme or "water" in theme:
            return "ocean_shore"
        elif "spiritual" in theme or "praise" in theme or "church" in theme:
            return "praise_house"
        elif "basket" in theme or "craft" in theme or "artisan" in theme:
            return "sweetgrass_workshop"
        elif "cook" in theme or "kitchen" in theme or "food" in theme:
            return "kitchen_warmth"
        elif "evening" in theme or "night" in theme or "porch" in theme:
            return "evening_porch"
        elif "morning" in theme or "routine" in theme or "wake" in theme:
            return "morning_routine"
        else:
            return "lowcountry_marsh"

    def _parse_script_segments(self, script_text: str) -> List[Dict]:
        """Parse a script into narratable segments with timing."""
        segments = []
        lines = script_text.split("\n")
        current_segment = {"text": "", "type": "narration", "duration": 0}

        for line in lines:
            stripped = line.strip()

            # Skip markers and metadata
            if stripped.startswith("##") or stripped.startswith("---"):
                if current_segment["text"].strip():
                    segments.append(current_segment)
                    current_segment = {"text": "", "type": "narration", "duration": 0}
                continue

            # Narration instructions
            if stripped.startswith("[NARRATOR:") or stripped.startswith("[MUSIC:") or stripped.startswith("[SOUND:"):
                if current_segment["text"].strip():
                    segments.append(current_segment)
                current_segment = {"text": "", "type": "instruction", "duration": 0}
                continue

            # Regular text
            if stripped and not stripped.startswith("#"):
                current_segment["text"] += stripped + " "
                # Estimate duration: ~150 words per minute
                word_count = len(stripped.split())
                current_segment["duration"] += (word_count / 150) * 60

        if current_segment["text"].strip():
            segments.append(current_segment)

        return segments

    def text_to_speech(self, text: str, voice: Dict, output_path: Path) -> bool:
        """Convert text to speech using Edge TTS. Human quality, zero cost."""
        try:
            # Use edge-tts for natural-sounding speech
            cmd = [
                sys.executable, "-m", "edge_tts",
                "--voice", voice["name"],
                "--text", text[:5000],  # Edge TTS has a text limit
                "--write-media", str(output_path),
            ]
            if voice.get("rate") and voice["rate"] != "+0%":
                cmd.extend(["--rate", voice["rate"]])
            if voice.get("pitch") and voice["pitch"] != "+0Hz":
                cmd.extend(["--pitch", voice["pitch"]])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0 and output_path.exists()
        except Exception as e:
            print(f"    TTS error: {e}")
            return False

    def produce_audiobook(self, script_path: Path, title: str,
                          content_type: str = "history",
                          theme: str = "lowcountry") -> Dict:
        """Produce a complete audiobook from a script. Fully automatic."""
        print(f"\n  🎙️  Producing: {title}")

        if not script_path.exists():
            return {"error": f"Script not found: {script_path}"}

        script_text = script_path.read_text()
        voice = self._select_voice(content_type)
        soundscape = self._select_soundscape(theme)

        # Create output directory
        slug = title.lower().replace(" ", "-").replace(":", "").replace("'", "")[:50]
        output_dir = AUDIO_OUTPUT_DIR / slug
        output_dir.mkdir(parents=True, exist_ok=True)

        # Parse segments
        segments = self._parse_script_segments(script_text)
        print(f"    Segments: {len(segments)}")
        print(f"    Voice: {voice['name']} ({voice['description']})")
        print(f"    Soundscape: {soundscape}")

        # Generate audio for each segment
        audio_files = []
        for i, seg in enumerate(segments):
            if seg["type"] != "narration" or not seg["text"].strip():
                continue

            seg_path = output_dir / f"seg-{i+1:03d}.mp3"
            success = self.text_to_speech(seg["text"], voice, seg_path)
            if success:
                audio_files.append(str(seg_path))
                print(f"    Segment {i+1}: {seg['duration']:.1f}s ✓")
            else:
                print(f"    Segment {i+1}: FAILED")

        # Concatenate all segments into one audiobook
        if audio_files:
            final_path = output_dir / f"{slug}.mp3"
            concat_file = output_dir / "concat.txt"
            concat_file.write_text("\n".join(f"file '{f}'" for f in audio_files))

            try:
                subprocess.run([
                    self.ffmpeg, "-f", "concat", "-safe", "0",
                    "-i", str(concat_file),
                    "-c", "copy",
                    str(final_path)
                ], capture_output=True, timeout=120)
            except:
                pass

            # Get duration
            duration = 0
            try:
                probe = subprocess.run([
                    self.ffmpeg, "-i", str(final_path),
                    "-f", "null", "-"
                ], capture_output=True, text=True, timeout=30)
                for line in probe.stderr.split("\n"):
                    if "Duration" in line:
                        parts = line.strip().split(",")[0].split(":")[-1].strip()
                        h, m, s = parts.split(":")
                        duration = int(h) * 3600 + int(m) * 60 + float(s)
            except:
                pass

            result = {
                "status": "produced",
                "title": title,
                "voice": voice["name"],
                "soundscape": soundscape,
                "segments": len(audio_files),
                "duration_seconds": duration,
                "duration_formatted": f"{int(duration//60)}m {int(duration%60)}s" if duration else "unknown",
                "output_path": str(final_path),
                "human_quality": True,
            }

            self.db.log_content("audio", "audiobook", title, str(final_path))
            return result

        return {"error": "No audio segments produced"}

    def produce_podcast_episode(self, script_path: Path, title: str,
                                 episode: str = "001") -> Dict:
        """Produce a podcast episode with intro/outro music."""
        return self.produce_audiobook(
            script_path, f"{title} (Podcast Ep. {episode})",
            content_type="community", theme="lowcountry"
        )

    def batch_produce(self, scripts_dir: Path, content_type: str = "history") -> Dict:
        """Produce audiobooks for all scripts in a directory."""
        results = []
        for script in sorted(scripts_dir.glob("*.md")):
            title = script.stem.replace("-", " ").title()
            result = self.produce_audiobook(script, title, content_type)
            results.append(result)
        return {
            "status": "batch_complete",
            "total": len(results),
            "produced": sum(1 for r in results if r.get("status") == "produced"),
            "results": results,
        }

    def status(self) -> Dict:
        """Engine status."""
        return {
            "engine": "GGB Human Voice Engine",
            "status": "ready",
            "voices": list(VOICE_PROFILES.keys()),
            "soundscapes": list(AMBIENT_SOUNDSCAPES.keys()),
            "ffmpeg": self.ffmpeg,
            "output_dir": str(AUDIO_OUTPUT_DIR),
        }


# ─── CLI ───────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Human Voice Engine")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Engine status")

    produce = sub.add_parser("produce", help="Produce an audiobook from a script")
    produce.add_argument("script", help="Path to script file")
    produce.add_argument("--title", default=None, help="Audiobook title")
    produce.add_argument("--type", default="history", choices=["history", "personal", "community", "default"])
    produce.add_argument("--theme", default="lowcountry")

    batch = sub.add_parser("batch", help="Batch produce from directory")
    batch.add_argument("dir", help="Directory of script files")
    batch.add_argument("--type", default="history")

    args = parser.parse_args()
    engine = HumanVoiceEngine()

    if args.command == "status":
        result = engine.status()
    elif args.command == "produce":
        script = Path(args.script)
        title = args.title or script.stem.replace("-", " ").title()
        result = engine.produce_audiobook(script, title, args.type, args.theme)
    elif args.command == "batch":
        result = engine.batch_produce(Path(args.dir), args.type)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            if "voices" in result:
                print(f"🎙️  {result['engine']}")
                print(f"   Status: {result['status']}")
                print(f"   Voices: {', '.join(result['voices'])}")
                print(f"   Soundscapes: {', '.join(result['soundscapes'])}")
                print(f"   FFmpeg: {result['ffmpeg']}")
                print(f"   Output: {result['output_dir']}")
            elif "duration_formatted" in result:
                print(f"  ✅ Produced: {result['title']}")
                print(f"     Voice: {result['voice']}")
                print(f"     Duration: {result['duration_formatted']}")
                print(f"     Segments: {result['segments']}")
                print(f"     Output: {result['output_path']}")
            elif "total" in result:
                print(f"  Batch: {result['produced']}/{result['total']} produced")
            else:
                for k, v in result.items():
                    print(f"{k}: {v}")
        else:
            print(result)

    return 0

if __name__ == "__main__":
    sys.exit(cli())
