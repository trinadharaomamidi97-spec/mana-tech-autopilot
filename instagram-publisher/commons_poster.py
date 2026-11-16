#!/usr/bin/env python3
"""Build one branded Telugu poster from a freely licensed Wikimedia Commons photo.

The script runs inside GitHub Actions, so no ChatGPT/Gmail/Drive binary handoff
is needed. It creates a staged manifest; the workflow commits the JPEG, checks
the public raw URL, and only then promotes the post to queued.
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

from PIL import Image, ImageDraw, ImageFont, ImageOps, features

REPO = "trinadharaomamidi97-spec/mana-tech-autopilot"
RAW_PREFIX = f"https://raw.githubusercontent.com/{REPO}/main/"
FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstelugu/"
    "NotoSansTelugu%5Bwdth%2Cwght%5D.ttf"
)
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
        "alt_text": "తంజావూరులోని బృహదీశ్వర ఆలయ గోపురం మరియు రాతి నిర్మాణాల ఫోటోపై తెలుగు చరిత్ర శీర్షికతో రూపొందించిన పోస్టర్.",
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
        thumb = info.get("thumburl") or info.get("url")
        if not thumb:
            continue
        width = int(info.get("thumbwidth") or info.get("width") or 0)
        height = int(info.get("thumbheight") or info.get("height") or 0)
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
    # Prefer wide or near-square photos with enough resolution for a poster.
    candidates.sort(key=lambda item: (item["width"] * item["height"], -abs(item["width"] / item["height"] - 1.0)), reverse=True)
    return candidates[0]

def load_font(font_path: Path, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(font_path), size, layout_engine=ImageFont.Layout.RAQM)
    if bold:
        try:
            axes = font.get_variation_axes()
            values = [axis.get("default", 0) for axis in axes]
            for index, axis in enumerate(axes):
                if "weight" in str(axis.get("name", "")).casefold():
                    values[index] = 800
            if axes:
                font.set_variation_by_axes(values)
        except (AttributeError, OSError, ValueError):
            pass
    return font

def wrap_by_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        box = draw.textbbox((0, 0), candidate, font=font, stroke_width=1)
        if current and box[2] - box[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines

def draw_text_block(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont,
                    fill: str, max_width: int, spacing: int, stroke_width: int = 0) -> int:
    lines = wrap_by_width(draw, text, font, max_width)
    draw.multiline_text(
        xy, "\n".join(lines), font=font, fill=fill, spacing=spacing,
        stroke_width=stroke_width, stroke_fill="#071226", align="left",
        direction="ltr", language="te",
    )
    return len(lines)

def make_poster(photo_bytes: bytes, topic: dict, photo: dict, font_path: Path, output_path: Path) -> None:
    from io import BytesIO

    with Image.open(BytesIO(photo_bytes)) as source:
        source = ImageOps.exif_transpose(source).convert("RGB")
        poster = ImageOps.fit(source, (1080, 1080), method=Image.Resampling.LANCZOS, centering=(0.5, 0.42))

    # Dark translucent title and information panels preserve the photo while keeping Telugu readable.
    overlay = Image.new("RGBA", poster.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle((38, 42, 1042, 620), radius=40, fill=(5, 16, 43, 222), outline=(255, 197, 53, 255), width=5)
    od.rounded_rectangle((40, 700, 1040, 1038), radius=34, fill=(5, 16, 43, 225), outline=(255, 197, 53, 255), width=4)
    poster = Image.alpha_composite(poster.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(poster)

    small = load_font(font_path, 30, bold=True)
    title_font = load_font(font_path, 76, bold=True)
    body_font = load_font(font_path, 36, bold=True)
    credit_font = load_font(font_path, 18)

    draw.rounded_rectangle((76, 78, 470, 140), radius=24, fill="#FFC52F")
    draw.text((100, 87), topic["category"], font=small, fill="#09152D", stroke_width=0)

    draw.rounded_rectangle((842, 68, 1000, 150), radius=24, fill="#0A1A3A", outline="#FFC52F", width=3)
    draw.text((865, 80), "MT", font=load_font(font_path, 42, bold=True), fill="#FFC52F")
    draw.text((676, 157), "MANA TECH TELUGU", font=load_font(font_path, 18, bold=True), fill="#FFFFFF")

    size = 76
    while size >= 48:
        title_font = load_font(font_path, size, bold=True)
        lines = wrap_by_width(draw, topic["title"], title_font, 890)
        height = len(lines) * (size + 20)
        if len(lines) <= 3 and height <= 360:
            break
        size -= 4
    draw_text_block(draw, (82, 225), topic["title"], title_font, "#FFFFFF", 890, 18, stroke_width=2)

    # One short supporting line at the bottom gives context without crowding the image.
    body_lines = wrap_by_width(draw, topic["cta"], body_font, 880)
    draw.multiline_text((82, 770), "\n".join(body_lines[:2]), font=body_font, fill="#FFD54D",
                        spacing=16, stroke_width=1, stroke_fill="#071226", direction="ltr", language="te")

    attribution = f"PHOTO: {photo['artist']}  •  WIKIMEDIA COMMONS  •  {photo['license']}"
    # Keep the on-image credit concise; complete links/terms are also in the Instagram caption.
    credit = attribution[:105]
    draw.text((82, 980), credit, font=credit_font, fill="#F2F4F8", stroke_width=0)

    poster = poster.convert("RGB")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    poster.save(output_path, format="JPEG", quality=90, optimize=True, progressive=True)
    if output_path.stat().st_size > 5 * 1024 * 1024:
        poster.save(output_path, format="JPEG", quality=84, optimize=True, progressive=True)
    with Image.open(output_path) as check:
        check.verify()
    if not any("\u0c00" <= ch <= "\u0c7f" for ch in topic["title"]):
        raise RuntimeError("The selected title does not contain Telugu text.")

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

    if not features.check("raqm"):
        raise RuntimeError("Pillow was built without libraqm; Telugu text shaping is unavailable.")

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

    cache = Path(tempfile.gettempdir()) / "mana-tech-font-cache"
    cache.mkdir(parents=True, exist_ok=True)
    font_path = cache / "NotoSansTelugu-variable.ttf"
    if not font_path.exists():
        font_path.write_bytes(http_get(FONT_URL))

    photo_bytes = http_get(photo["image_url"])
    if len(photo_bytes) < 10000:
        raise RuntimeError("Commons returned an unexpectedly small image file.")
    make_poster(photo_bytes, topic, photo, font_path, image_path)

    attribution = (
        f"📷 Photo: {photo['artist']} / Wikimedia Commons. "
        f"Source: {photo['page_url']}. License: {photo['license']} "
        f"{photo['license_url']}. Modified: Telugu title and graphic design added. "
        f"The adapted poster is shared under {poster_license}."
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
            "alt_text": topic["alt_text"],
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
                "modification": "Telugu title, text panel, crop and visual design added.",
                "adapted_poster_license": poster_license,
            },
        }],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    size_kb = image_path.stat().st_size / 1024
    print(f"Created {image_path} ({size_kb:.1f} KB)")
    print(f"Created staged manifest {manifest_path}")
    print("The workflow must commit the JPEG, verify its public raw URL, and promote staged -> queued before publishing.")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Commons poster preparation failed safely: {exc}")
        raise SystemExit(1)
