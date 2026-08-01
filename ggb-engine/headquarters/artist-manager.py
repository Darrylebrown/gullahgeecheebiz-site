#!/usr/bin/env python3
"""
GGB Artist Management System — profiles, catalogs, release schedules,
collaboration matching, and royalty tracking for multiple artists.
Wires into the Human Voice Engine, Music Studio, and Distribution Pipeline.
"""
import json, sys, uuid, random, sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from headquarters.engine import HQDatabase, STUDIO_DIR, CONTENT_DIR, LOGS_DIR
from publisher import REPO_ROOT

ARTISTS_DB = LOGS_DIR / "artists.db"

# ─── Artist Profiles ───────────────────────────────────────────────────────

@dataclass
class ArtistProfile:
    """A GGB artist — musician, narrator, or audio creator."""
    artist_id: str = ""
    name: str = ""
    stage_name: str = ""
    bio: str = ""
    genre: str = "ambient"
    voice_profile: str = "narrator_male"
    social_links: Dict = field(default_factory=lambda: {"tiktok": "", "instagram": "", "youtube": ""})
    catalog_count: int = 0
    total_streams: int = 0
    total_revenue: float = 0.0
    joined_at: str = ""
    status: str = "active"  # active, on_break, archived

# ─── Artist Database ──────────────────────────────────────────────────────

class ArtistDatabase:
    """Persistent store for artists, releases, and royalties."""

    def __init__(self, db_path: Path = ARTISTS_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS artists (
                artist_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                stage_name TEXT,
                bio TEXT DEFAULT '',
                genre TEXT DEFAULT 'ambient',
                voice_profile TEXT DEFAULT 'narrator_male',
                social_links TEXT DEFAULT '{}',
                catalog_count INTEGER DEFAULT 0,
                total_streams INTEGER DEFAULT 0,
                total_revenue REAL DEFAULT 0.0,
                joined_at TEXT NOT NULL,
                status TEXT DEFAULT 'active'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS releases (
                release_id TEXT PRIMARY KEY,
                artist_id TEXT NOT NULL,
                title TEXT NOT NULL,
                release_type TEXT NOT NULL,  -- single, ep, album, audiobook
                genre TEXT,
                duration_seconds INTEGER DEFAULT 0,
                streams INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0.0,
                status TEXT DEFAULT 'draft',  -- draft, mastering, ready, published
                release_date TEXT,
                created_at TEXT NOT NULL,
                published_at TEXT,
                FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS royalties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id TEXT NOT NULL,
                release_id TEXT,
                platform TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                period_start TEXT,
                period_end TEXT,
                paid INTEGER DEFAULT 0,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS collaborations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                release_id TEXT NOT NULL,
                artist_id TEXT NOT NULL,
                role TEXT NOT NULL,  -- lead, featured, producer, writer
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def add_artist(self, profile: ArtistProfile) -> str:
        conn = sqlite3.connect(str(self.db_path))
        if not profile.artist_id:
            profile.artist_id = f"ggb-artist-{uuid.uuid4().hex[:8]}"
        if not profile.joined_at:
            profile.joined_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO artists (artist_id, name, stage_name, bio, genre, voice_profile, social_links, joined_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (profile.artist_id, profile.name, profile.stage_name, profile.bio, profile.genre,
             profile.voice_profile, json.dumps(profile.social_links), profile.joined_at, profile.status)
        )
        conn.commit()
        conn.close()
        return profile.artist_id

    def get_artist(self, artist_id: str) -> Optional[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute("SELECT * FROM artists WHERE artist_id=?", (artist_id,)).fetchone()
        conn.close()
        if row:
            return {
                "artist_id": row[0], "name": row[1], "stage_name": row[2],
                "bio": row[3], "genre": row[4], "voice_profile": row[5],
                "social_links": json.loads(row[6]), "catalog_count": row[7],
                "total_streams": row[8], "total_revenue": row[9],
                "joined_at": row[10], "status": row[11],
            }
        return None

    def list_artists(self, status: str = "active") -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute("SELECT * FROM artists WHERE status=? ORDER BY joined_at DESC", (status,)).fetchall()
        conn.close()
        return [{
            "artist_id": r[0], "name": r[1], "stage_name": r[2],
            "genre": r[4], "catalog_count": r[7], "total_streams": r[8],
            "total_revenue": r[9], "joined_at": r[10], "status": r[11],
        } for r in rows]

    def add_release(self, artist_id: str, title: str, release_type: str = "single",
                    genre: str = "", duration: int = 0) -> str:
        release_id = f"ggb-release-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO releases (release_id, artist_id, title, release_type, genre, duration_seconds, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (release_id, artist_id, title, release_type, genre, duration, now)
        )
        # Update artist catalog count
        conn.execute("UPDATE artists SET catalog_count = catalog_count + 1 WHERE artist_id=?", (artist_id,))
        conn.commit()
        conn.close()
        return release_id

    def get_releases(self, artist_id: str, status: str = "") -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        if status:
            rows = conn.execute(
                "SELECT * FROM releases WHERE artist_id=? AND status=? ORDER BY created_at DESC",
                (artist_id, status)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM releases WHERE artist_id=? ORDER BY created_at DESC",
                (artist_id,)
            ).fetchall()
        conn.close()
        return [{
            "release_id": r[0], "artist_id": r[1], "title": r[2],
            "release_type": r[3], "genre": r[4], "duration_seconds": r[5],
            "streams": r[6], "revenue": r[7], "status": r[8],
            "release_date": r[9], "created_at": r[10], "published_at": r[11],
        } for r in rows]

    def record_royalty(self, artist_id: str, amount: float, platform: str = "distrokid",
                       release_id: str = "", period: str = ""):
        conn = sqlite3.connect(str(self.db_path))
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO royalties (artist_id, release_id, platform, amount, period_start, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
            (artist_id, release_id, platform, amount, period, now)
        )
        conn.execute("UPDATE artists SET total_revenue = total_revenue + ? WHERE artist_id=?", (amount, artist_id))
        conn.commit()
        conn.close()

    def get_royalties(self, artist_id: str) -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute(
            "SELECT * FROM royalties WHERE artist_id=? ORDER BY recorded_at DESC LIMIT 50",
            (artist_id,)
        ).fetchall()
        conn.close()
        return [{
            "id": r[0], "artist_id": r[1], "release_id": r[2],
            "platform": r[3], "amount": r[4], "currency": r[5],
            "period": r[6], "paid": r[8], "recorded_at": r[9],
        } for r in rows]


# ─── Artist Manager ──────────────────────────────────────────────────────

class ArtistManager:
    """Manages artists, releases, collaborations, and royalties."""

    def __init__(self, db: ArtistDatabase = None):
        self.db = db or ArtistDatabase()
        self.hq = HQDatabase()

    def onboard_artist(self, name: str, stage_name: str = "",
                       genre: str = "ambient", bio: str = "") -> Dict:
        """Onboard a new artist into the system."""
        profile = ArtistProfile(
            name=name,
            stage_name=stage_name or name,
            bio=bio or f"{name} — Gullah Geechee Biz artist",
            genre=genre,
            voice_profile="narrator_male" if genre in ("ambient", "cinematic", "history") else "narrator_female_warm",
        )
        artist_id = self.db.add_artist(profile)
        self.hq.log_content("artists", "onboard", f"Artist: {name}", "")
        return {"status": "onboarded", "artist_id": artist_id, "name": name, "genre": genre}

    def create_release(self, artist_id: str, title: str,
                       release_type: str = "single", genre: str = "") -> Dict:
        """Create a new release for an artist."""
        artist = self.db.get_artist(artist_id)
        if not artist:
            return {"error": "Artist not found"}
        release_id = self.db.add_release(artist_id, title, release_type, genre or artist["genre"])
        self.hq.log_content("artists", "release", f"Release: {title} ({artist['name']})", "")
        return {
            "status": "created",
            "release_id": release_id,
            "artist": artist["name"],
            "title": title,
            "type": release_type,
        }

    def generate_music_prompt(self, artist_id: str, theme: str = "gullah") -> Dict:
        """Generate a Suno AI music prompt for an artist's release."""
        artist = self.db.get_artist(artist_id)
        if not artist:
            return {"error": "Artist not found"}
        # Use the music studio to generate a prompt
        from headquarters.music_studio import MusicStudio
        studio = MusicStudio()
        prompt = studio.generate_prompt(theme, artist["genre"])
        return {
            "status": "generated",
            "artist": artist["name"],
            "genre": artist["genre"],
            "prompt": prompt["prompt"],
        }

    def produce_audiobook(self, artist_id: str, script_path: str, title: str) -> Dict:
        """Produce an audiobook narrated by the artist."""
        artist = self.db.get_artist(artist_id)
        if not artist:
            return {"error": "Artist not found"}
        from headquarters.human_voice_engine import HumanVoiceEngine
        engine = HumanVoiceEngine()
        result = engine.produce_audiobook(Path(script_path), title, artist["genre"])
        if result.get("status") == "produced":
            self.db.add_release(artist_id, title, "audiobook", artist["genre"], int(result.get("duration_seconds", 0)))
        return result

    def catalog_report(self, artist_id: str = "") -> Dict:
        """Full catalog report for one or all artists."""
        if artist_id:
            artists = [self.db.get_artist(artist_id)]
        else:
            artists = self.db.list_artists()

        report = []
        for artist in artists:
            if not artist:
                continue
            releases = self.db.get_releases(artist["artist_id"])
            royalties = self.db.get_royalties(artist["artist_id"])
            total_royalties = sum(r["amount"] for r in royalties)
            report.append({
                "artist": artist["name"],
                "stage_name": artist.get("stage_name", ""),
                "genre": artist["genre"],
                "catalog_count": len(releases),
                "published": sum(1 for r in releases if r["status"] == "published"),
                "in_progress": sum(1 for r in releases if r["status"] in ("draft", "mastering")),
                "total_streams": artist.get("total_streams", 0),
                "total_revenue": total_royalties,
                "recent_releases": releases[:3] if releases else [],
            })

        return {
            "total_artists": len(report),
            "total_releases": sum(r["catalog_count"] for r in report),
            "total_revenue": sum(r["total_revenue"] for r in report),
            "artists": report,
        }

    def dashboard(self) -> Dict:
        """Quick dashboard of artist ecosystem."""
        artists = self.db.list_artists()
        total_releases = sum(len(self.db.get_releases(a["artist_id"])) for a in artists)
        return {
            "module": "GGB Artist Management",
            "status": "active",
            "total_artists": len(artists),
            "total_releases": total_releases,
            "active_artists": len(artists),
            "genres": list(set(a["genre"] for a in artists)),
            "artists": [{"name": a["name"], "genre": a["genre"], "catalog": a["catalog_count"]} for a in artists],
        }


# ─── CLI ───────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Artist Management System")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("dashboard", help="Artist ecosystem dashboard")
    sub.add_parser("catalog", help="Full catalog report")

    onboard = sub.add_parser("onboard", help="Onboard a new artist")
    onboard.add_argument("name", help="Artist name")
    onboard.add_argument("--stage", default="", help="Stage name")
    onboard.add_argument("--genre", default="ambient", help="Primary genre")
    onboard.add_argument("--bio", default="", help="Artist bio")

    release = sub.add_parser("release", help="Create a new release")
    release.add_argument("artist_id", help="Artist ID")
    release.add_argument("title", help="Release title")
    release.add_argument("--type", default="single", choices=["single", "ep", "album", "audiobook"])
    release.add_argument("--genre", default="", help="Genre override")

    prompt = sub.add_parser("prompt", help="Generate music prompt for artist")
    prompt.add_argument("artist_id", help="Artist ID")
    prompt.add_argument("--theme", default="gullah", help="Music theme")

    audio = sub.add_parser("audio", help="Produce audiobook for artist")
    audio.add_argument("artist_id", help="Artist ID")
    audio.add_argument("script", help="Path to script file")
    audio.add_argument("--title", default="", help="Audiobook title")

    args = parser.parse_args()
    mgr = ArtistManager()

    if args.command == "dashboard":
        result = mgr.dashboard()
    elif args.command == "catalog":
        result = mgr.catalog_report()
    elif args.command == "onboard":
        result = mgr.onboard_artist(args.name, args.stage, args.genre, args.bio)
    elif args.command == "release":
        result = mgr.create_release(args.artist_id, args.title, args.type, args.genre)
    elif args.command == "prompt":
        result = mgr.generate_music_prompt(args.artist_id, args.theme)
    elif args.command == "audio":
        title = args.title or Path(args.script).stem.replace("-", " ").title()
        result = mgr.produce_audiobook(args.artist_id, args.script, title)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            if "module" in result:
                print(f"🎵 {result['module']}")
                print(f"   Artists: {result['total_artists']}")
                print(f"   Releases: {result['total_releases']}")
                print(f"   Genres: {', '.join(result['genres'])}")
                for a in result["artists"]:
                    print(f"     {a['name']:>20} | {a['genre']:>12} | {a['catalog']} releases")
            elif "total_artists" in result:
                print(f"🎵 GGB Artist Catalog")
                print(f"   Artists: {result['total_artists']}")
                print(f"   Releases: {result['total_releases']}")
                print(f"   Revenue: ${result['total_revenue']:.2f}")
                print()
                for a in result["artists"]:
                    print(f"  {a['artist']:>25} | {a['genre']:>12} | {a['catalog_count']} releases | ${a['total_revenue']:.2f}")
            elif "artist_id" in result:
                print(f"✅ {result.get('status', 'ok').title()}: {result.get('name', result.get('artist', ''))}")
                if "release_id" in result:
                    print(f"   Release: {result['release_id']}")
                if "prompt" in result:
                    print(f"   Prompt: {result['prompt'][:100]}...")
            else:
                for k, v in result.items():
                    print(f"{k}: {v}")
        else:
            print(result)

    return 0

if __name__ == "__main__":
    sys.exit(cli())
