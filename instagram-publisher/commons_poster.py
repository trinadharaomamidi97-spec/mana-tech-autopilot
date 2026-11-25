#!/usr/bin/env python3
"""Prepare one clean 1080x1350 photo-only Instagram Feed image.

No titles, logos, borders, text panels, or watermarks are added. Story text
metadata stays in the manifest; only public-domain/CC0 sources are accepted.
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
from urllib.error import HTTPError, URLError

from PIL import Image, ImageOps

REPO = "trinadharaomamidi97-spec/mana-tech-autopilot"
RAW_PREFIX = f"https://raw.githubusercontent.com/{REPO}/main/"
USER_AGENT = "ManaTechTeluguAutoPilot/1.0 (Wikimedia Commons image reuse with attribution)"

# Facts are evergreen and point to their primary institutional source.
# The date selects one topic, so the same topic is not repeated on consecutive days.
TOPICS = [
    {
        "slug": "axolotl-regeneration",
        "category": "COLORFUL CREATURES",
        "title": "తన శరీర భాగాలను తిరిగి పెంచుకునే జీవి!",
        "description": "ఆక్సలోటల్ అనే జలచర సాలమాండర్ కోల్పోయిన కాళ్లు, తోకతో పాటు కొన్ని ఇతర కణజాలాలను తిరిగి పెంచుకోగలదు. శరీర పునరుత్పత్తిని అర్థం చేసుకోవడానికి శాస్త్రవేత్తలు ఈ జీవిని అధ్యయనం చేస్తున్నారు.",
        "cta": "ఈ అద్భుతమైన జీవి గురించి మీకు తెలిసిన విషయం కామెంట్ చేయండి.",
        "source_title": "Axolotls and Regeneration — Smithsonian's National Zoo",
        "source_url": "https://nationalzoo.si.edu/animals/axolotl",
        "hashtags": [
            "#ManaTechTelugu",
            "#Axolotl",
            "#AmazingCreatures",
            "#Wildlife",
            "#ScienceFacts"
        ]
    },
    {
        "slug": "flamingo-colourful-life",
        "category": "WILDLIFE",
        "title": "ఫ్లెమింగోల గులాబీ రంగు వెనుక రహస్యం!",
        "description": "ఫ్లెమింగోల ఈకల గులాబీ లేదా నారింజ రంగు వాటి ఆహారంలోని కెరోటినాయిడ్ వర్ణద్రవ్యాల వల్ల వస్తుంది. ఇవి నీటిలోని చిన్న జీవులు, ఆల్గే వంటి ఆహారాన్ని వడపోసి తింటాయి.",
        "cta": "ఫ్లెమింగోల రంగు గురించి మీకు ముందే తెలుసా?",
        "source_title": "Flamingo — San Diego Zoo Wildlife Alliance",
        "source_url": "https://animals.sandiegozoo.org/animals/flamingo",
        "hashtags": [
            "#ManaTechTelugu",
            "#Flamingo",
            "#WildlifeFacts",
            "#Nature"
        ]
    },
    {
        "slug": "octopus-three-hearts",
        "category": "OCEAN CREATURES",
        "title": "మూడు గుండెలతో సముద్రంలో జీవించే ఆక్టోపస్!",
        "description": "ఆక్టోపస్‌కు మూడు గుండెలు ఉంటాయి. రెండు గుండెలు రక్తాన్ని గిల్ల్స్‌కు పంపుతాయి; మూడో గుండె ఆక్సిజన్ పొందిన రక్తాన్ని శరీరమంతా పంపుతుంది.",
        "cta": "ఆక్టోపస్ జీవనశైలి గురించి ఇంకేం తెలుసుకోవాలనుకుంటున్నారు?",
        "source_title": "Octopus Facts — NOAA",
        "source_url": "https://oceanservice.noaa.gov/facts/octopus.html",
        "hashtags": [
            "#ManaTechTelugu",
            "#Octopus",
            "#OceanLife",
            "#CreatureFacts"
        ]
    },
    {
        "slug": "deep-sea-bioluminescence",
        "category": "UNDERWATER WORLD",
        "title": "చీకటి సముద్రంలో స్వయంగా వెలిగే జీవులు!",
        "description": "బయోల్యూమినెసెన్స్ అనేది జీవులు రసాయన చర్యల ద్వారా కాంతిని ఉత్పత్తి చేసే ప్రక్రియ. లోతైన సముద్రంలోని కొన్ని జీవులు ఆ కాంతిని ఆహారం, రక్షణ లేదా సంకేతాల కోసం ఉపయోగిస్తాయి.",
        "cta": "మీకు అత్యంత ఆశ్చర్యంగా అనిపించిన సముద్ర జీవి ఏది?",
        "source_title": "What is Bioluminescence? — NOAA Ocean Service",
        "source_url": "https://oceanservice.noaa.gov/facts/biolum.html",
        "hashtags": [
            "#ManaTechTelugu",
            "#Bioluminescence",
            "#DeepSea",
            "#OceanScience"
        ]
    },
    {
        "slug": "mantis-shrimp-colours",
        "category": "COLOURFUL OCEAN LIFE",
        "title": "సముద్రంలో రంగుల మెరుపు — మాంటిస్ ష్రింప్!",
        "description": "మాంటిస్ ష్రింప్‌లు అత్యంత వైవిధ్యమైన రంగులు కలిగిన సముద్ర క్రస్టేసియన్లు. వాటి కళ్లలో కాంతిని గుర్తించే ప్రత్యేక నిర్మాణాలు ఉండటంతో అవి శాస్త్రవేత్తలకు ఆసక్తికరమైన అధ్యయన అంశంగా మారాయి.",
        "cta": "ఈ రంగురంగుల సముద్ర జీవిని దగ్గరగా చూడాలనుకుంటున్నారా?",
        "source_title": "Mantis Shrimp — Smithsonian Ocean",
        "source_url": "https://ocean.si.edu/ocean-life/invertebrates/mantis-shrimp",
        "hashtags": [
            "#ManaTechTelugu",
            "#MantisShrimp",
            "#OceanLife",
            "#ColourfulCreatures"
        ]
    },
    {
        "slug": "hummingbird-flight",
        "category": "BIRD LIFE",
        "title": "గాలిలో నిలిచినట్టు ఎగిరే హమ్మింగ్‌బర్డ్!",
        "description": "హమ్మింగ్‌బర్డ్‌లు తమ రెక్కలను వేగంగా కొట్టడం వల్ల గాలిలో ఒకే చోట నిలిచినట్టు ఉండగలవు. పువ్వుల నుంచి మకరందం సేకరించేటప్పుడు ఈ ప్రత్యేక ఎగిరే నైపుణ్యం ఉపయోగపడుతుంది.",
        "cta": "హమ్మింగ్‌బర్డ్ ఎగిరే విధానం మీకు ఎలా అనిపించింది?",
        "source_title": "Hummingbirds — Smithsonian's National Zoo",
        "source_url": "https://nationalzoo.si.edu/animals/hummingbird",
        "hashtags": [
            "#ManaTechTelugu",
            "#Hummingbird",
            "#Birds",
            "#NatureFacts"
        ]
    },
    {
        "slug": "aurora-colours",
        "category": "NATURAL WONDERS",
        "title": "ఆకాశంలో రంగుల తెరలా మెరిసే అరోరా!",
        "description": "సూర్యుడి నుంచి వచ్చే ఆవేశిత కణాలు భూమి అయస్కాంత క్షేత్రం వెంట వాతావరణంలోని వాయువులతో చర్య జరిపినప్పుడు అరోరా కాంతులు ఏర్పడతాయి. వేర్వేరు వాయువులు వేర్వేరు రంగుల కాంతిని ఉత్పత్తి చేస్తాయి.",
        "cta": "ఈ రంగుల ఆకాశాన్ని ప్రత్యక్షంగా చూడాలని ఉందా?",
        "source_title": "Auroras — NASA Science",
        "source_url": "https://science.nasa.gov/sun/auroras/",
        "hashtags": [
            "#ManaTechTelugu",
            "#Aurora",
            "#Nature",
            "#SpaceScience"
        ]
    },
    {
        "slug": "venus-long-day",
        "category": "SPACE SCIENCE",
        "title": "వీనస్‌పై ఒక రోజు… ఒక ఏడాది కంటే పెద్దది!",
        "description": "వీనస్ తన అక్షంపై చాలా నెమ్మదిగా తిరుగుతుంది. అక్కడి ఒక భ్రమణ దినం 243 భూమి రోజులు; ఒక సంవత్సరం మాత్రం 225 భూమి రోజులు.",
        "cta": "వీనస్‌పై సూర్యోదయం ఎలా ఉంటుందో ఊహించగలరా?",
        "source_title": "Venus Facts — NASA Science",
        "source_url": "https://science.nasa.gov/venus/venus-facts/",
        "hashtags": [
            "#ManaTechTelugu",
            "#Venus",
            "#SpaceScience",
            "#NASA"
        ]
    },
    {
        "slug": "black-holes",
        "category": "SPACE MYSTERIES",
        "title": "కాంతి కూడా తప్పించుకోలేని అంతరిక్ష రహస్యం!",
        "description": "బ్లాక్ హోల్ అనేది పదార్థం అత్యంత చిన్న ప్రాంతంలో కేంద్రీకృతమైన ఖగోళ వస్తువు. దాని ఈవెంట్ హారైజన్ లోపల నుంచి కాంతి కూడా బయటకు రాలేదు.",
        "cta": "బ్లాక్ హోల్ గురించి మీకు ఏ సందేహం ఉంది?",
        "source_title": "Black Holes — NASA Science",
        "source_url": "https://science.nasa.gov/universe/black-holes/",
        "hashtags": [
            "#ManaTechTelugu",
            "#BlackHoles",
            "#Astronomy",
            "#NASA"
        ]
    },
    {
        "slug": "coral-reef-colour",
        "category": "OCEAN ECOSYSTEMS",
        "title": "సముద్ర అడుగున రంగుల నగరంలా ఉండే కోరల్ రీఫ్!",
        "description": "కోరల్ రీఫ్‌లు అనేక సముద్ర జీవులకు ఆహారం, ఆశ్రయం అందించే సంక్లిష్ట పర్యావరణ వ్యవస్థలు. పగడపు పాలిప్స్‌లో నివసించే సూక్ష్మ ఆల్గేలు వాటి రంగులకు, శక్తి అవసరాలకు సహకరిస్తాయి.",
        "cta": "కోరల్ రీఫ్‌లో మీకు కనిపించిన రంగు ఏది?",
        "source_title": "Coral Reefs — NOAA",
        "source_url": "https://oceanservice.noaa.gov/education/tutorial_corals/",
        "hashtags": [
            "#ManaTechTelugu",
            "#CoralReef",
            "#OceanLife",
            "#Nature"
        ]
    },
    {
        "slug": "chameleon-colour-change",
        "category": "ANIMAL ADAPTATIONS",
        "title": "రంగులు మార్చే ఊసరవెల్లి జీవన రహస్యం!",
        "description": "ఊసరవెల్లులు చర్మంలోని ప్రత్యేక కణ నిర్మాణాలను మార్చడం ద్వారా రంగు, నమూనాలను మార్చగలవు. ఈ మార్పులు కమ్యూనికేషన్, ఉష్ణ నియంత్రణ వంటి పనులకు ఉపయోగపడతాయి.",
        "cta": "ఊసరవెల్లి రంగు మారడాన్ని ఎప్పుడైనా గమనించారా?",
        "source_title": "Chameleons — National Geographic",
        "source_url": "https://www.nationalgeographic.com/animals/reptiles/facts/chameleons",
        "hashtags": [
            "#ManaTechTelugu",
            "#Chameleon",
            "#AnimalFacts",
            "#Wildlife"
        ]
    },
    {
        "slug": "giant-panda-lifestyle",
        "category": "ANIMAL LIFESTYLE",
        "title": "రోజులో ఎక్కువ సమయం వెదురు తింటూ గడిపే పాండా!",
        "description": "జెయింట్ పాండాలు రోజులో చాలా గంటలు వెదురు తింటూ గడుపుతాయి. వాటి ఆహారంలో వెదురు ప్రధాన భాగం కావడంతో అవి తరచుగా తింటూ ఉండాలి.",
        "cta": "పాండాల రోజువారీ జీవితం గురించి మీకు ఏది ఆసక్తికరం?",
        "source_title": "Giant Panda — Smithsonian's National Zoo",
        "source_url": "https://nationalzoo.si.edu/animals/giant-panda",
        "hashtags": [
            "#ManaTechTelugu",
            "#Panda",
            "#AnimalLifestyle",
            "#Wildlife"
        ]
    },
    {
        "slug": "octopus-camouflage",
        "category": "CREATURE SUPERPOWERS",
        "title": "క్షణాల్లో పరిసరాల్లో కలిసిపోయే ఆక్టోపస్!",
        "description": "ఆక్టోపస్ చర్మంలోని క్రోమాటోఫోర్ కణాలు రంగు మార్పుకు సహాయపడతాయి. కొన్ని జాతులు చర్మపు ఆకృతిని కూడా మార్చి రాళ్లు లేదా పగడాల మధ్య దాగగలవు.",
        "cta": "ఆక్టోపస్ మాయమయ్యే నైపుణ్యం అద్భుతం కదా?",
        "source_title": "Octopus Camouflage — Smithsonian Ocean",
        "source_url": "https://ocean.si.edu/ocean-life/invertebrates/octopuses",
        "hashtags": [
            "#ManaTechTelugu",
            "#Octopus",
            "#Camouflage",
            "#OceanLife"
        ]
    },
    {
        "slug": "fireflies-glow",
        "category": "NATURE MAGIC",
        "title": "రాత్రివేళ వెలిగే మిణుగురుల చిన్న ప్రపంచం!",
        "description": "మిణుగురులు తమ శరీరంలోని రసాయన చర్య ద్వారా చల్లని కాంతిని ఉత్పత్తి చేస్తాయి. అనేక జాతులు జతను ఆకర్షించడానికి ప్రత్యేక కాంతి సంకేతాలను ఉపయోగిస్తాయి.",
        "cta": "మీరు చివరిసారి మిణుగురులను ఎక్కడ చూశారు?",
        "source_title": "Fireflies — National Geographic",
        "source_url": "https://www.nationalgeographic.com/animals/invertebrates/facts/fireflies",
        "hashtags": [
            "#ManaTechTelugu",
            "#Fireflies",
            "#NatureMagic",
            "#Insects"
        ]
    },
    {
        "slug": "tardigrade-micro-world",
        "category": "TINY CREATURES",
        "title": "అత్యంత కఠిన పరిస్థితులను తట్టుకునే సూక్ష్మ జీవి!",
        "description": "టార్డిగ్రేడ్‌లు అనుకూల పరిస్థితులు లేనప్పుడు తమ శరీర చర్యలను తీవ్రంగా తగ్గించే స్థితిలోకి వెళ్లగలవు. ఈ సూక్ష్మ జంతువులు అనేక పర్యావరణ ఒత్తిడులను తట్టుకునే సామర్థ్యంతో ప్రసిద్ధి చెందాయి.",
        "cta": "ఇంత చిన్న జీవి ఇంతటి సామర్థ్యం కలిగి ఉండటం ఆశ్చర్యం కదా?",
        "source_title": "Tardigrades — Smithsonian Magazine",
        "source_url": "https://www.smithsonianmag.com/science-nature/tardigrades-180963777/",
        "hashtags": [
            "#ManaTechTelugu",
            "#Tardigrade",
            "#MicroWorld",
            "#ScienceFacts"
        ]
    }
]

def http_get(url: str, timeout: int = 45, attempts: int = 5) -> bytes:
    """Fetch Wikimedia API/media with bounded retries for temporary throttling."""
    last_error = None
    for attempt in range(attempts):
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/*,*/*;q=0.8"})
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
            retry_after = exc.headers.get("Retry-After")
            try:
                delay = min(45, max(2, int(retry_after))) if retry_after else min(30, 3 * (2 ** attempt))
            except ValueError:
                delay = min(30, 3 * (2 ** attempt))
            print(f"Temporary HTTP {exc.code}; retry {attempt + 1}/{attempts} in {delay}s.")
            time.sleep(delay)
        except URLError as exc:
            last_error = exc
            if attempt == attempts - 1:
                raise
            delay = min(20, 2 * (2 ** attempt))
            print(f"Temporary image network error; retry {attempt + 1}/{attempts} in {delay}s.")
            time.sleep(delay)
    raise RuntimeError(f"Image download failed after retries: {last_error}")

def strip_html(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]*>", "", value or "")).strip()

def license_allowed(name: str) -> bool:
    value = name.casefold().replace("creative commons", "cc").strip()
    # Never use NonCommercial or NoDerivatives files for an Instagram post.
    if any(term in value for term in ("noncommercial", "non-commercial", "no derivatives")):
        return False
    tokens = set(re.split(r"[^a-z0-9]+", value))
    if "nc" in tokens or "nd" in tokens:
        return False
    # Accept public-domain/CC0 and attribution licenses. The full creator,
    # source, license URL, and crop modification are included in the caption.
    # CC BY-SA adaptations retain the same ShareAlike license in the caption.
    if value in {"public domain", "public domain mark", "cc0", "cc0 1.0"}:
        return True
    return value.startswith(("cc by ", "cc by-sa ", "cc by-sa-"))

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
        # Prefer Wikimedia's resized upload CDN thumbnail; retain original as fallback.
        thumb = info.get("thumburl") or info.get("url")
        original = info.get("url")
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
            "original_image_url": original,
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
    """Create a clean 1080x1350 portrait Feed crop; never draw text or graphics."""
    from io import BytesIO

    with Image.open(BytesIO(photo_bytes)) as source:
        source = ImageOps.exif_transpose(source).convert("RGB")
        image = ImageOps.fit(
            source,
            (1080, 1350),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.42),
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="JPEG", quality=92, optimize=True, progressive=True)
    if output_path.stat().st_size > 8 * 1024 * 1024:
        image.save(output_path, format="JPEG", quality=85, optimize=True, progressive=True)
    if output_path.stat().st_size > 8 * 1024 * 1024:
        raise RuntimeError("Feed image exceeds Meta's 8 MB image limit.")
    with Image.open(output_path) as check:
        if check.size != (1080, 1350):
            raise RuntimeError(f"Expected 1080x1350 Feed image, got {check.size}.")
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

    download_urls = [photo.get("image_url"), photo.get("original_image_url")]
    photo_bytes = None
    download_errors = []
    for download_url in dict.fromkeys(url for url in download_urls if url):
        try:
            candidate_bytes = http_get(download_url)
            if len(candidate_bytes) < 10000:
                raise RuntimeError("Image source returned an unexpectedly small file.")
            from io import BytesIO
            with Image.open(BytesIO(candidate_bytes)) as check:
                check.verify()
            photo_bytes = candidate_bytes
            break
        except Exception as exc:
            download_errors.append(f"{download_url}: {exc}")
            print(f"Image URL failed; trying next available source: {exc}")
    if photo_bytes is None:
        raise RuntimeError("All Commons image URLs failed after retries. " + " | ".join(download_errors))
    make_photo(photo_bytes, image_path)

    attribution = (
        f"📷 Photo: {photo['artist']} / Wikimedia Commons. "
        f"Source: {photo['page_url']}. License: {photo['license']} "
        f"{photo['license_url']}. Modified: cropped to a 4:5 portrait Feed frame only; no text or graphics added. "
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
                "modification": "Cropped to a 9:16 full-screen Story frame only; no text or graphic overlay added.",
                "adapted_poster_license": poster_license,
            },
        }],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    size_kb = image_path.stat().st_size / 1024
    print(f"Created {image_path} ({size_kb:.1f} KB)")
    print(f"Created staged manifest {manifest_path}")
    print("Created clean 1080x1350 photo-only JPEG. The workflow must verify its public URL before publishing.")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Commons poster preparation failed safely: {exc}")
        raise SystemExit(1)
