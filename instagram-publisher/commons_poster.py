#!/usr/bin/env python3
"""Prepare one clean, photorealistic 9:16 image from a freely licensed Commons photo.

No titles, logos, borders, text panels, or watermarks are added to the image.
All Telugu copy and attribution stay in the Instagram caption.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

REPO = "trinadharaomamidi97-spec/mana-tech-autopilot"
RAW_PREFIX = f"https://raw.githubusercontent.com/{REPO}/main/"
USER_AGENT = "ManaTechTeluguAutoPilot/1.0 (Wikimedia Commons image reuse with attribution)"

# Facts are evergreen and point to their primary institutional source.
# The date selects one topic, so the same topic is not repeated on consecutive days.
TOPICS = [
    {
        "slug": "brihadisvara",
        "category": "CHOLA HISTORY",
        "commons_query": "Brihadisvara Temple Thanjavur",
        "title": "చోళుల వైభవానికి సజీవ సాక్ష్యం!",
        "description": (
            "తంజావూరులోని బృహదీశ్వర ఆలయం రాజరాజ చోళుడు నిర్మించిన ప్రసిద్ధ చోళ దేవాలయం. "
            "ఇది UNESCO గుర్తించిన Great Living Chola Temples సమూహంలో భాగం; ఈ వారసత్వ ప్రదేశం 1987లో జాబితాలో చేరింది."
        ),
        "cta": "చోళుల శిల్పకళలో మీకు నచ్చిన అంశం ఏది? కామెంట్ చేయండి.",
        "alt_text": "తంజావూరులోని బృహదీశ్వర ఆలయ రాతి నిర్మాణాల ఫోటోపై తెలుగు చరిత్ర శీర్షిక, వివరణ ప్యానెల్ మరియు Mana Tech Telugu గుర్తుతో రూపొందించిన పోస్టర్.",
        "source_title": "Great Living Chola Temples — UNESCO World Heritage Centre",
        "source_url": "https://whc.unesco.org/en/list/250/",
        "hashtags": ["#ManaTechTelugu", "#CholaHistory", "#BrihadisvaraTemple", "#Thanjavur", "#UNESCO", "#IndianHeritage", "#TeluguHistory"],
    },
    {
        "slug": "hampi",
        "category": "VIJAYANAGARA HISTORY",
        "commons_query": "Hampi Vittala Temple stone chariot",
        "title": "హంపి రాతి రథం వెనుక అద్భుత కథ!",
        "description": (
            "కర్ణాటకలోని హంపి విజయనగర సామ్రాజ్య రాజధాని అవశేషాలకు ప్రసిద్ధి. "
            "విఠ్ఠల ఆలయ సముదాయంలోని రాతి రథం హంపి శిల్పకళకు గుర్తుగా నిలిచింది; హంపి 1986లో UNESCO ప్రపంచ వారసత్వ జాబితాలో చేరింది."
        ),
        "cta": "హంపిలో మీరు చూడాలనుకునే నిర్మాణం ఏది?",
        "alt_text": "హంపిలోని విఠ్ఠల ఆలయ రాతి రథం ఫోటోతో రూపొందించిన తెలుగు వారసత్వ పోస్టర్.",
        "source_title": "Group of Monuments at Hampi — UNESCO World Heritage Centre",
        "source_url": "https://whc.unesco.org/en/list/241/",
        "hashtags": ["#ManaTechTelugu", "#Hampi", "#Vijayanagara", "#IndianHistory", "#UNESCOWorldHeritage", "#TeluguFacts"],
    },
    {
        "slug": "konark",
        "category": "ANCIENT INDIA",
        "commons_query": "Konark Sun Temple Odisha",
        "title": "సూర్యుడి రథంలా నిర్మించిన ఆలయం!",
        "description": (
            "ఒడిశాలోని కోణార్క్ సూర్య దేవాలయం సూర్య భగవానుడి రథాన్ని పోలిన నిర్మాణ రూపకల్పనకు ప్రసిద్ధి. "
            "ఈ 13వ శతాబ్దపు ఆలయం 1984లో UNESCO ప్రపంచ వారసత్వ ప్రదేశంగా గుర్తింపు పొందింది."
        ),
        "cta": "ఈ రథాకార ఆలయ నిర్మాణం మీకు ఎలా అనిపించింది?",
        "alt_text": "ఒడిశాలోని కోణార్క్ సూర్య దేవాలయ రాతి నిర్మాణం ఫోటోతో రూపొందించిన తెలుగు పోస్టర్.",
        "source_title": "Sun Temple, Konârak — UNESCO World Heritage Centre",
        "source_url": "https://whc.unesco.org/en/list/246/",
        "hashtags": ["#ManaTechTelugu", "#Konark", "#SunTemple", "#Odisha", "#IndianArchitecture", "#UNESCO"],
    },
    {
        "slug": "ajanta",
        "category": "INDIAN ART HISTORY",
        "commons_query": "Ajanta Caves Maharashtra",
        "title": "రాతిలో చెక్కిన అద్భుత కళా ప్రపంచం!",
        "description": (
            "మహారాష్ట్రలోని అజంతా గుహలు బౌద్ధ సంప్రదాయానికి చెందిన శిలా నిర్మాణాలు, చిత్రకళకు ప్రసిద్ధి. "
            "ఈ గుహలు 1983లో UNESCO ప్రపంచ వారసత్వ జాబితాలో చేరాయి."
        ),
        "cta": "అజంతా గుహల చిత్రకళ గురించి మీకు తెలుసా?",
        "alt_text": "మహారాష్ట్రలోని అజంతా గుహల ముఖభాగం లేదా శిలా నిర్మాణం ఫోటోతో రూపొందించిన తెలుగు పోస్టర్.",
        "source_title": "Ajanta Caves — UNESCO World Heritage Centre",
        "source_url": "https://whc.unesco.org/en/list/242/",
        "hashtags": ["#ManaTechTelugu", "#AjantaCaves", "#IndianArt", "#BuddhistHeritage", "#UNESCO", "#TeluguHistory"],
    },
    {
        "slug": "ellora",
        "category": "INDIAN ARCHITECTURE",
        "commons_query": "Ellora Caves Kailasa temple",
        "title": "ఒకే కొండలో చెక్కిన మహా ఆలయం!",
        "description": (
            "ఎల్లోరా గుహల్లోని కైలాస ఆలయం ఒకే రాతి కొండను పై నుంచి కిందికి తొలిచి రూపొందించిన విశేష నిర్మాణం. "
            "ఎల్లోరా గుహ సముదాయం 1983లో UNESCO ప్రపంచ వారసత్వ జాబితాలో చేరింది."
        ),
        "cta": "ఇలాంటి రాతి నిర్మాణాన్ని చూసి ఆశ్చర్యపోతున్నారా?",
        "alt_text": "ఎల్లోరాలోని కైలాస ఆలయ శిలా నిర్మాణం ఫోటోతో రూపొందించిన తెలుగు చరిత్ర పోస్టర్.",
        "source_title": "Ellora Caves — UNESCO World Heritage Centre",
        "source_url": "https://whc.unesco.org/en/list/243/",
        "hashtags": ["#ManaTechTelugu", "#ElloraCaves", "#KailasaTemple", "#IndianArchitecture", "#UNESCO", "#History"],
    },
    {
        "slug": "sanchi",
        "category": "BUDDHIST HERITAGE",
        "commons_query": "Sanchi Great Stupa India",
        "title": "సాంచీ స్థూపం చెప్పే చరిత్ర!",
        "description": (
            "మధ్యప్రదేశ్‌లోని సాంచీ బౌద్ధ స్మారక కట్టడాలకు ప్రసిద్ధి. "
            "అక్కడి మహా స్థూపం భారతదేశంలోని ప్రాచీన బౌద్ధ వారసత్వాన్ని చూపిస్తుంది; సాంచీ 1989లో UNESCO జాబితాలో చేరింది."
        ),
        "cta": "సాంచీ స్థూపం గురించి ఇంకేం తెలుసుకోవాలనుకుంటున్నారు?",
        "alt_text": "మధ్యప్రదేశ్‌లోని సాంచీ మహా స్థూపం ఫోటోతో రూపొందించిన తెలుగు పోస్టర్.",
        "source_title": "Buddhist Monuments at Sanchi — UNESCO World Heritage Centre",
        "source_url": "https://whc.unesco.org/en/list/524/",
        "hashtags": ["#ManaTechTelugu", "#Sanchi", "#BuddhistHeritage", "#MadhyaPradesh", "#UNESCO", "#IndianHistory"],
    },
    {
        "slug": "rani-ki-vav",
        "category": "ANCIENT ENGINEERING",
        "commons_query": "Rani ki Vav Patan Gujarat",
        "title": "భూమి కింద దాగిన శిల్పాల ప్రపంచం!",
        "description": (
            "గుజరాత్‌లోని రాణి కి వావ్ ఒక అద్భుతమైన మెట్ల బావి. "
            "దాని గోడలపై ఉన్న శిల్పాలు, స్థాయిలుగా దిగే నిర్మాణం భారతదేశపు చారిత్రక నీటి నిర్వహణ కళను తెలియజేస్తాయి."
        ),
        "cta": "ఇలాంటి మెట్ల బావిని ప్రత్యక్షంగా చూడాలనుకుంటున్నారా?",
        "alt_text": "గుజరాత్‌లోని రాణి కి వావ్ మెట్ల బావి శిల్పాలు కనిపించే ఫోటోతో రూపొందించిన తెలుగు పోస్టర్.",
        "source_title": "Rani-ki-Vav (the Queen’s Stepwell) — UNESCO World Heritage Centre",
        "source_url": "https://whc.unesco.org/en/list/922/",
        "hashtags": ["#ManaTechTelugu", "#RaniKiVav", "#Stepwell", "#GujaratHeritage", "#IndianArchitecture", "#UNESCO"],
    },
    {
        "slug": "mahabalipuram",
        "category": "PALLAVA HISTORY",
        "commons_query": "Mahabalipuram Shore Temple monuments",
        "title": "సముద్ర తీరాన పల్లవుల శిల్ప వైభవం!",
        "description": (
            "తమిళనాడులోని మహాబలిపురం పల్లవుల కాలానికి చెందిన రాతి ఆలయాలు, శిల్పాలకు ప్రసిద్ధి. "
            "ఇక్కడి స్మారక కట్టడాల సమూహం 1984లో UNESCO ప్రపంచ వారసత్వ జాబితాలో చేరింది."
        ),
        "cta": "మహాబలిపురం శిల్పాల్లో మీకు నచ్చింది ఏది?",
        "alt_text": "తమిళనాడులోని మహాబలిపురం సముద్రతీర ఆలయ లేదా రాతి స్మారక కట్టడం ఫోటోతో రూపొందించిన తెలుగు పోస్టర్.",
        "source_title": "Group of Monuments at Mahabalipuram — UNESCO World Heritage Centre",
        "source_url": "https://whc.unesco.org/en/list/249",
        "hashtags": ["#ManaTechTelugu", "#Mahabalipuram", "#PallavaHistory", "#TamilNadu", "#UNESCO", "#IndianHeritage"],
    },
]

def http_get(url: str, timeout: int = 45) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read()

def strip_html(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]*>", "", value or "")).strip()

def license_allowed(name: str) -> bool:
    value = name.casefold().replace("creative commons", "cc").strip()
    if "noncommercial" in value or "non-commercial" in value or "nc" in value.split():
        return False
    if "no derivatives" in value or "nd" in value.split():
        return False
    if value in {"public domain", "cc0", "cc0 1.0", "public domain mark"}:
        return True
    return bool(re.fullmatch(r"cc by(?:-sa)? (?:1\.0|2\.0|2\.5|3\.0|4\.0)", value))

def search_commons(topic: dict) -> dict:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": topic["commons_query"],
        "gsrnamespace": "6",
        "gsrlimit": "40",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": "1800",
        "format": "json",
        "formatversion": "2",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urlencode(params)
    payload = json.loads(http_get(url).decode("utf-8"))
    pages = payload.get("query", {}).get("pages", [])
    if isinstance(pages, dict):
        pages = list(pages.values())

    candidates = []
    for page in pages:
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        ext = info.get("extmetadata") or {}
        license_name = strip_html((ext.get("LicenseShortName") or {}).get("value", ""))
        license_url = strip_html((ext.get("LicenseUrl") or {}).get("value", ""))
        artist = strip_html((ext.get("Artist") or {}).get("value", ""))
        if not license_allowed(license_name):
            continue
        if not artist and not license_name.casefold().startswith(("cc0", "public domain")):
            continue
        mime = info.get("mime", "")
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            continue
        thumb = info.get("url") or info.get("thumburl")
        if not thumb:
            continue
        width = int(info.get("width") or info.get("thumbwidth") or 0)
        height = int(info.get("height") or info.get("thumbheight") or 0)
        if min(width, height) < 900:
            continue
        page_url = "https://commons.wikimedia.org/wiki/" + quote(page["title"].replace(" ", "_"), safe=":_(),'")
        candidates.append({
            "title": page["title"],
            "image_url": thumb,
            "page_url": page_url,
            "artist": artist or "Unknown (public-domain/CC0 file)",
            "license": license_name,
            "license_url": license_url,
            "width": width,
            "height": height,
            "description": strip_html((ext.get("ImageDescription") or {}).get("value", "")),
        })
    if not candidates:
        raise RuntimeError(f"No sufficiently large, explicitly licensed Commons photo found for: {topic['commons_query']}")
    # Prefer source photos closest to a portrait 9:16 frame, with high resolution.
    target_ratio = 9 / 16
    candidates.sort(key=lambda item: (abs(item["width"] / item["height"] - target_ratio), -(item["width"] * item["height"])))
    return candidates[0]

def make_photo(photo_bytes: bytes, output_path: Path) -> None:
    """Create a clean 1080x1920 portrait crop; never draw text or graphics."""
    from io import BytesIO

    with Image.open(BytesIO(photo_bytes)) as source:
        source = ImageOps.exif_transpose(source).convert("RGB")
        image = ImageOps.fit(
            source,
            (1080, 1920),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.42),
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="JPEG", quality=93, optimize=True, progressive=True)
    if output_path.stat().st_size > 8 * 1024 * 1024:
        image.save(output_path, format="JPEG", quality=88, optimize=True, progressive=True)
    with Image.open(output_path) as check:
        if check.size != (1080, 1920):
            raise RuntimeError(f"Expected 1080x1920 portrait image, got {check.size}.")
        check.verify()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Post date YYYY-MM-DD")
    parser.add_argument("--output-root", default=".", help="Repository root or temporary preview folder")
    parser.add_argument("--dry-run", action="store_true", help="Build preview files without touching the live repository")
    args = parser.parse_args()

    post_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    root = Path(args.output_root).resolve()
    manifest_path = root / "posts" / f"{args.date}.json"
    image_path = root / "posts" / "images" / args.date / "post-01.jpg"

    if manifest_path.exists() and not args.dry_run:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("posts"):
            print(f"Manifest already exists for {args.date}; refusing to overwrite it.")
            return 0

    base = date(2026, 11, 17)
    topic = TOPICS[(post_date - base).days % len(TOPICS)]
    print(f"Selected topic: {topic['slug']} — {topic['title']}")

    photo = search_commons(topic)
    print(f"Commons photo: {photo['title']} | {photo['artist']} | {photo['license']}")
    if "SA" in photo["license"].upper() or "BY-SA" in photo["license"].upper():
        poster_license = photo["license"]
    elif photo["license"].casefold().startswith("cc by"):
        poster_license = photo["license"]
    else:
        poster_license = "CC0 1.0 / Public Domain"

    photo_bytes = http_get(photo["image_url"])
    if len(photo_bytes) < 10000:
        raise RuntimeError("Commons returned an unexpectedly small image file.")
    make_photo(photo_bytes, image_path)

    attribution = (
        f"📷 Photo: {photo['artist']} / Wikimedia Commons. "
        f"Source: {photo['page_url']}. License: {photo['license']} "
        f"{photo['license_url']}. Modified: cropped to a 9:16 portrait frame only; no text or graphics added. "
        f"The adapted image is shared under {poster_license}."
    )
    manifest = {
        "date": args.date,
        "posts": [{
            "id": f"{args.date}-01",
            "status": "staged",
            "topic": topic["slug"],
            "language": "te",
            "title": topic["title"],
            "description": topic["description"],
            "call_to_action": topic["cta"] + "\n\n" + attribution,
            "hashtags": topic["hashtags"],
            "image_url": RAW_PREFIX + f"posts/images/{args.date}/post-01.jpg",
            "alt_text": f"Clean, photorealistic vertical 9:16 photograph of {topic['slug'].replace('-', ' ')}; no text or graphic overlay.",
            "is_factual": True,
            "sources": [{
                "title": topic["source_title"],
                "url": topic["source_url"],
                "checked_at": args.date,
            }],
            "photo_attribution": {
                "artist": photo["artist"],
                "commons_file": photo["title"],
                "source_url": photo["page_url"],
                "license": photo["license"],
                "license_url": photo["license_url"],
                "modification": "Cropped to a 9:16 portrait frame only; no text or graphic overlay added.",
                "adapted_poster_license": poster_license,
            },
        }],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    size_kb = image_path.stat().st_size / 1024
    print(f"Created {image_path} ({size_kb:.1f} KB)")
    print(f"Created staged manifest {manifest_path}")
    print("Created clean 1080x1920 photo-only JPEG. The workflow must verify its public URL before publishing.")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Commons poster preparation failed safely: {exc}")
        raise SystemExit(1)
