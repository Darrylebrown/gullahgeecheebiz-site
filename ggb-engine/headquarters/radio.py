#!/usr/bin/env python3
"""
GGB Radio Station — Automated playlist generator and streaming scheduler.
Generates themed playlists from music prompts, schedules radio shows.
"""
import json, sys, uuid, random
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from headquarters.engine import HQDatabase, STUDIO_DIR, LOGS_DIR

# ─── Radio Schedule ─────────────────────────────────────────────────────────

SHOWS = [
    {"name": "Gullah Morning Rise", "time": "06:00", "duration": 120, "genre": "ambient, folk"},
    {"name": "Lowcountry Midday", "time": "12:00", "duration": 60, "genre": "blues, folk"},
    {"name": "Sweetgrass Evening", "time": "18:00", "duration": 90, "genre": "world, ambient"},
    {"name": "Sea Islands Night", "time": "22:00", "duration": 120, "genre": "ambient, cinematic"},
    {"name": "Gullah Gospel Hour", "time": "08:00", "duration": 60, "genre": "gospel, spiritual"},
    {"name": "Rice Field Rhythms", "time": "15:00", "duration": 60, "genre": "folk, work songs"},
    {"name": "Basket Weaving Beats", "time": "20:00", "duration": 90, "genre": "world, percussion"},
]

class RadioStation:
    """GGB Radio Station — automated playlist generation and scheduling."""

    def __init__(self, db: HQDatabase = None):
        self.db = db or HQDatabase()

    def generate_playlist(self, genre: str = "ambient", duration_minutes: int = 60) -> dict:
        """Generate a playlist for a given genre and duration."""
        tracks = []
        track_duration = 180  # average 3 min per track
        num_tracks = max(1, duration_minutes * 60 // track_duration)

        for i in range(num_tracks):
            tracks.append({
                "track": i + 1,
                "title": f"{genre.title} Movement {i + 1}",
                "duration": track_duration,
                "genre": genre,
                "bpm": random.choice([70, 80, 90, 100, 110, 120]),
                "key": random.choice(["C", "G", "D", "A", "E", "F", "Bb", "Eb"]),
            })

        playlist = {
            "name": f"{genre.title} Playlist",
            "generated": datetime.now(timezone.utc).isoformat(),
            "duration_minutes": duration_minutes,
            "tracks": len(tracks),
            "track_list": tracks,
        }

        output = STUDIO_DIR / f"playlist-{genre}-{uuid.uuid4().hex[:6]}.json"
        output.write_text(json.dumps(playlist, indent=2))
        self.db.log_content("radio", "playlist", playlist["name"], str(output))
        return playlist

    def generate_show_schedule(self, date: str = None) -> dict:
        """Generate a full day's radio schedule."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        schedule = []
        for show in SHOWS:
            schedule.append({
                "time": show["time"],
                "name": show["name"],
                "duration": show["duration"],
                "genre": show["genre"],
                "playlist": self.generate_playlist(show["genre"].split(",")[0].strip(), show["duration"]),
            })

        output = STUDIO_DIR / f"schedule-{date}.json"
        output.write_text(json.dumps({"date": date, "shows": len(schedule), "schedule": schedule}, indent=2))
        self.db.log_content("radio", "schedule", f"Schedule {date}", str(output))
        return {"date": date, "shows": len(schedule), "schedule": schedule}

    def status(self) -> dict:
        return {
            "station": "GGB Radio",
            "shows": len(SHOWS),
            "daily_hours": sum(s["duration"] for s in SHOWS) / 60,
            "genres": list(set(s["genre"] for s in SHOWS)),
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Radio Station")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Radio station status")
    sub.add_parser("schedule", help="Generate today's schedule")
    playlist = sub.add_parser("playlist", help="Generate a playlist")
    playlist.add_argument("--genre", default="ambient")
    playlist.add_argument("--duration", type=int, default=60)

    args = parser.parse_args()
    radio = RadioStation()

    if args.command == "status":
        result = radio.status()
    elif args.command == "schedule":
        result = radio.generate_show_schedule()
    elif args.command == "playlist":
        result = radio.generate_playlist(args.genre, args.duration)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            for k, v in result.items():
                print(f"{k}: {v}")
        else:
            print(result)
