#!/usr/bin/env python3
"""Build premium bundle ZIPs: box set (vol 1-25), heritage vault (50 vols + genealogy + audio), license."""
import zipfile, glob, re, os, shutil
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
EPUB_DIR = BASE / "publish" / "for-distribution" / "google-play"
OUT_DIR = BASE / "publish" / "premium-bundles"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def find_volumes():
    vols = {}
    for f in glob.glob(str(EPUB_DIR / "*.epub")):
        try:
            z = zipfile.ZipFile(f)
            opf = [n for n in z.namelist() if n.endswith(".opf")]
            if not opf:
                continue
            content = z.read(opf[0]).decode("utf-8", "ignore")
            m = re.search(r"<dc:title[^>]*>(.*?)</dc:title>", content, re.S)
            if not m:
                continue
            vm = re.match(r"encyclopedia\s*volume\s*(\d+)", m.group(1).strip(), re.I)
            if vm:
                vols[int(vm.group(1))] = f
        except Exception:
            continue
    return vols

def build_box_set(vols):
    out = OUT_DIR / "ggb-encyclopedia-box-set-vol-1-25.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for v in range(1, 26):
            if v in vols:
                z.write(vols[v], f"Encyclopedia Volume {v:02d}.epub")
        readme = (
            "GULLAH GEECHEE ENCYCLOPEDIA — COMPLETE BOX SET (Volumes 1-25)\n"
            "by Darryl Elliott Brown\n\n"
            "This bundle contains the complete 25-volume Gullah Geechee Encyclopedia.\n"
            "Includes volumes 01 through 25 in EPUB format — readable on any device.\n\n"
            "© 2026 Gullah Geechee Biz. All rights reserved.\n"
        )
        z.writestr("README.txt", readme)
    return out

def build_vault(vols, audio_files, genealogy):
    out = OUT_DIR / "ggb-heritage-vault.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for v in range(1, 51):
            if v in vols:
                z.write(vols[v], f"Encyclopedia Volume {v:02d}.epub")
        for a in audio_files:
            z.write(a, f"audio/{Path(a).name}")
        if genealogy:
            z.write(genealogy, "genealogy-tracker/index.html")
        readme = (
            "ULTIMATE GULLAH GEECHEE HERITAGE VAULT\n"
            "by Darryl Elliott Brown\n\n"
            "Includes:\n"
            "- Complete 50-volume Gullah Geechee Encyclopedia (EPUB)\n"
            "- Gullah Geechee Genealogy Tracker (interactive HTML tool)\n"
            "- Gullah Geechee audio content (MP3)\n\n"
            "© 2026 Gullah Geechee Biz. All rights reserved.\n"
        )
        z.writestr("README.txt", readme)
    return out

def build_license(vols, audio_files, genealogy):
    out = OUT_DIR / "ggb-institutional-site-license.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for v in range(1, 51):
            if v in vols:
                z.write(vols[v], f"Encyclopedia Volume {v:02d}.epub")
        for a in audio_files:
            z.write(a, f"audio/{Path(a).name}")
        if genealogy:
            z.write(genealogy, "genealogy-tracker/index.html")
        license_txt = (
            "GULLAH GEECHEE INSTITUTIONAL SITE LICENSE\n\n"
            "This license grants the purchasing institution (library, university, museum, "
            "or cultural organization) a non-exclusive, perpetual site-wide license to "
            "distribute the included Gullah Geechee Encyclopedia volumes and materials "
            "to its patrons, students, and members.\n\n"
            "Permitted uses:\n"
            "- Campus/library-wide digital lending and access\n"
            "- Course reserves and classroom use\n"
            "- Public display at cultural institutions\n\n"
            "Not permitted: resale, republication, or redistribution outside the licensed "
            "institution without separate written agreement.\n\n"
            "© 2026 Gullah Geechee Biz. All rights reserved.\n"
        )
        z.writestr("LICENSE.txt", license_txt)
        z.writestr("README.txt", "Gullah Geechee Institutional Site License bundle.\n")
    return out

def main():
    vols = find_volumes()
    print(f"volumes found: {len(vols)} (1-{max(vols) if vols else 0})")
    audio = sorted(glob.glob(str(BASE / "publish" / "magazines" / "**" / "audio" / "*.mp3"), recursive=True))
    print(f"audio files: {len(audio)}")
    genealogy = str(BASE / "tools" / "gullah-genealogy-tracker" / "index.html")
    print(f"genealogy exists: {os.path.exists(genealogy)}")

    box = build_box_set(vols)
    print(f"box set: {box} ({box.stat().st_size/1024:.0f} KB)")
    vault = build_vault(vols, audio, genealogy)
    print(f"vault: {vault} ({vault.stat().st_size/1024:.0f} KB)")
    lic = build_license(vols, audio, genealogy)
    print(f"license: {lic} ({lic.stat().st_size/1024:.0f} KB)")

if __name__ == "__main__":
    main()
