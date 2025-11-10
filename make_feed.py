#!/usr/bin/env python3
import os, time, email.utils, html, sys, re
from urllib.parse import quote
from pathlib import Path

# --- CONFIG ---
BASE_DIR = Path("/home/pi/share/198k")      # where your audio files live
BASE_URL = "http://zigbee.local/198k"     # how your iPhone reaches them
FEED_PATH = BASE_DIR / "feed.xml"
ART_NAME  = "artwork.jpg"
ART_PATH  = BASE_DIR / ART_NAME
MAX_ITEMS = 50
AUDIO_EXTS = (".mp3", ".wav", ".m4a")       # prefer mp3 first

TITLE  = "198 kHz Shipping Forecast"
DESC   = "Automated 198 kHz Shipping Forecast recordings via KiwiSDR."
LANG   = "en-gb"
AUTHOR = "KiwiSDR capture on zigbee"

# --- HELPERS ---
def rfc2822(t): return email.utils.formatdate(t, usegmt=True)

def list_audio():
    """Return [(mtime, filename, size)] newest first, limited to MAX_ITEMS"""
    items = []
    for p in BASE_DIR.iterdir():
        if not p.is_file(): continue
        if not p.name.lower().endswith(AUDIO_EXTS): continue
        try:
            st = p.stat()
        except Exception:
            continue
        items.append((st.st_mtime, p.name, st.st_size))
    items.sort(reverse=True)
    return items[:MAX_ITEMS]

def guess_type(name: str) -> str:
    n = name.lower()
    if n.endswith(".mp3"): return "audio/mpeg"
    if n.endswith(".m4a"): return "audio/mp4"
    return "audio/wav"

# Filename pattern: ShippingFCST-YYMMDD_AM_051900UTC--host--avg-36.wav
FNPAT = re.compile(
    r"ShippingFCST-(\d{6})_(AM|PM)_(\d{6})UTC--(.+?)--avg-(\d+)\.[^\.]+$", re.IGNORECASE
)

def parse_from_filename(name: str):
    """Return dict with date, ampm, time, host_short, avg_int or {} if N/A."""
    m = FNPAT.search(name)
    if not m:
        return {}
    yymmdd, ampm, hhmmss, host_short, avg_int = m.groups()
    return {
        "yymmdd": yymmdd,
        "ampm": ampm,
        "hhmmss": hhmmss,
        "host_short": host_short,
        "avg_int": int(avg_int),
    }

def parse_ampm_time_str(name: str) -> str:
    """Return 'AM 05:19 UTC' for titles."""
    d = parse_from_filename(name)
    if not d: return ""
    hhmm = f"{d['hhmmss'][:2]}:{d['hhmmss'][2:4]}"
    return f"{d['ampm']} {hhmm} UTC"

def read_sidecar(for_audio: Path) -> str | None:
    """Return sidecar text contents if present, else None."""
    txt = for_audio.with_suffix(".txt")
    try:
        if txt.exists() and txt.is_file():
            return txt.read_text(encoding="utf-8")
    except Exception:
        pass
    return None

def make_desc(name: str, mtime: float, fallback_info: dict) -> str:
    """
    Build a description/summary string.
    Prefer sidecar text; otherwise synthesize a compact block.
    """
    audio_path = BASE_DIR / name
    side = read_sidecar(audio_path)
    if side:
        # Wrap in minimal lines; many apps show plain text (no HTML needed)
        return side.strip()

    # Fallback: synthesize from filename + mtime
    ampm_str = parse_ampm_time_str(name) or ""
    host = fallback_info.get("host_short", "unknown")
    avg  = fallback_info.get("avg_int", "??")
    # We only know mtime; show pubDate in RFC2822 below. Keep desc simple.
    lines = [
        f"Shipping Forecast – {ampm_str}".strip(),
        f"Receiver host: {host}",
        "Freq: 198 kHz, Mode: am",
        f"Average RSSI (label): -{avg} dBFS",
        "",
        "CREDIT / ORIGIN:",
        "  Received via KiwiSDR network (https://kiwisdr.com)",
        "  Please credit the receiver operator where possible.",
    ]
    return "\n".join(lines)

def make_item(name, size, mtime):
    url   = f"{BASE_URL}/{quote(name)}"
    ctype = guess_type(name)
    guid  = html.escape(name)
    pub   = rfc2822(mtime)

    # Title
    time_str = parse_ampm_time_str(name)
    base_title = os.path.splitext(name)[0]
    title = f"Shipping Forecast – {time_str}" if time_str else base_title

    # Description (and iTunes summary) — prefer sidecar; else synthesize
    fallback = parse_from_filename(name)
    desc = make_desc(name, mtime, fallback)
    # Escape for XML (keep it plain text for max compatibility)
    desc_xml = html.escape(desc)

    return f"""  <item>
    <title>{html.escape(title)}</title>
    <pubDate>{pub}</pubDate>
    <enclosure url="{url}" length="{size}" type="{ctype}"/>
    <guid isPermaLink="false">{guid}</guid>
    <description>{desc_xml}</description>
    <itunes:summary>{desc_xml}</itunes:summary>
  </item>"""

def build_feed():
    items = list_audio()
    print(f"[make_feed] found {len(items)} audio files", file=sys.stdout)
    if not items:
        print("[make_feed] no audio files — not writing feed", file=sys.stdout)
        return None

    art_url = f"{BASE_URL}/{quote(ART_NAME)}" if ART_PATH.exists() else None
    channel_items = "\n".join(make_item(n, s, t) for t, n, s in items)
    now = rfc2822(time.time())

    head = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{html.escape(TITLE)}</title>
  <link>{BASE_URL}/</link>
  <description>{html.escape(DESC)}</description>
  <language>{html.escape(LANG)}</language>
  <lastBuildDate>{now}</lastBuildDate>
  <atom:link rel="self" type="application/rss+xml" href="{BASE_URL}/feed.xml"/>
  <itunes:author>{html.escape(AUTHOR)}</itunes:author>
  <itunes:summary>{html.escape(DESC)}</itunes:summary>
  <itunes:category text="News">
    <itunes:category text="Weather"/>
  </itunes:category>
'''
    if art_url:
        head += f"""  <image>
    <url>{art_url}</url>
    <title>{html.escape(TITLE)}</title>
    <link>{BASE_URL}/</link>
  </image>
  <itunes:image href="{art_url}" />
"""
    tail = "\n</channel>\n</rss>\n"

    xml = head + "\n" + channel_items + tail
    FEED_PATH.write_text(xml, encoding="utf-8")
    print(f"[make_feed] wrote {FEED_PATH}", file=sys.stdout)
    return str(FEED_PATH)

if __name__ == "__main__":
    out = build_feed()
    if out: print("Wrote", out)
