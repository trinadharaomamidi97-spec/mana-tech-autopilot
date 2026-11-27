#!/usr/bin/env python3
"""Generate a four-image photo-only carousel and an independent Story image.

Cloudflare Workers AI creates the artwork; this script only crops and saves it.
Captions stay in the Instagram manifest and are never drawn onto images.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

from PIL import Image, ImageOps
from commons_poster import RAW_PREFIX, TOPICS
from cloudflare_image import cloudflare_generate, save_variants

ROOT = Path(__file__).resolve().parents[1]
BASE_DATE = date(2026, 11, 17)
REPO = "trinadharaomamidi97-spec/mana-tech-autopilot"
FEED_SLIDES = 4
TELUGU_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansTeluguUI-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansTelugu-VF.ttf",
    "/usr/share/fonts/truetype/lohit-telugu/Lohit-Telugu.ttf",
)



def _legacy_topic(slug: str) -> dict:
    return next(item for item in TOPICS if item["slug"] == slug)


# Only science, wildlife, nature and world-curiosity topics are eligible here.
# Temple and heritage entries in the legacy Commons list are intentionally excluded.
TOPIC_ROTATION = [
    _legacy_topic("octopus-three-hearts"),
    _legacy_topic("deep-sea-bioluminescence"),
    _legacy_topic("venus-long-day"),
    _legacy_topic("black-holes"),
    {
        "slug": "axolotl-regeneration", "category": "ANIMAL BIOLOGY",
        "title": "తన శరీర భాగాలను తిరిగి పెంచుకునే జీవి!",
        "description": "ఆక్సొలాటిల్ అనే సాలమాండర్ తన కాళ్లు, తోకతో పాటు కొన్ని ఇతర శరీర భాగాలను కూడా తిరిగి పెంచుకోగలదు. ఈ ప్రత్యేక సామర్థ్యాన్ని శాస్త్రవేత్తలు కణజాల పునరుత్పత్తిని అర్థం చేసుకోవడానికి అధ్యయనం చేస్తున్నారు.",
        "cta": "ఈ జీవి గురించి మీకు ఆశ్చర్యంగా అనిపించిన విషయం ఏది?",
        "source_title": "Axolotl — Smithsonian's National Zoo",
        "source_url": "https://nationalzoo.si.edu/animals/axolotl",
        "hashtags": ["#ManaTechTelugu", "#Axolotl", "#AnimalFacts", "#Wildlife", "#Science"],
    },
    {
        "slug": "aurora-lights", "category": "SPACE & NATURE",
        "title": "ఆకాశంలో రంగుల కాంతుల నాట్యం!",
        "description": "అరోరా కాంతులు సూర్యుడి నుంచి వచ్చిన విద్యుత్ ఆవేశిత కణాలు భూమి వాతావరణంలోని వాయువులతో పరస్పరం చర్య చేసినప్పుడు ఏర్పడతాయి. ఈ ప్రక్రియ వల్ల ధ్రువ ప్రాంతాల ఆకాశంలో ఆకుపచ్చ, గులాబీ, ఊదా వంటి రంగులు కనిపించవచ్చు.",
        "cta": "ఈ రంగుల ఆకాశాన్ని ప్రత్యక్షంగా చూడాలనుకుంటున్నారా?",
        "source_title": "Auroras — NASA Science",
        "source_url": "https://science.nasa.gov/sun/auroras/",
        "hashtags": ["#ManaTechTelugu", "#Aurora", "#NorthernLights", "#SpaceScience", "#Nature"],
    },
    {
        "slug": "honeybee-waggle-dance", "category": "ANIMAL BEHAVIOUR",
        "title": "తేనెటీగలు నాట్యంతో దారి చెబుతాయి!",
        "description": "ఆహారం ఉన్న ప్రదేశం దిశ, దూరం గురించి తేనెటీగలు తమ గూడు సహచరాలకు వాగుల్ డాన్స్ ద్వారా సంకేతాలు ఇస్తాయి. నాట్యంలో శరీరాన్ని కదిలించే తీరు ఆహార వనరుల స్థానాన్ని తెలియజేయడంలో సహాయపడుతుంది.",
        "cta": "ఇలాంటి సమాచార వ్యవస్థను ఊహించగలరా?",
        "source_title": "Bee Communication — USDA Agricultural Research Service",
        "source_url": "https://www.ars.usda.gov/",
        "hashtags": ["#ManaTechTelugu", "#HoneyBees", "#AnimalBehaviour", "#NatureFacts", "#Science"],
    },
    {
        "slug": "coral-reef-life", "category": "OCEAN LIFE",
        "title": "సముద్రంలో రంగుల నగరాలు!",
        "description": "పగడపు దిబ్బలు అనేక సముద్ర జీవులకు ఆహారం, ఆశ్రయం అందించే సంక్లిష్ట పర్యావరణ వ్యవస్థలు. పగడాలు చిన్న జంతువులు; వాటిలో నివసించే సూక్ష్మ శైవలాలతో ఉన్న సంబంధం వాటి జీవనానికి ముఖ్యమైనది.",
        "cta": "పగడపు దిబ్బల్లో మీకు కనిపించాలనుకునే జీవి ఏది?",
        "source_title": "Corals and Coral Reefs — NOAA",
        "source_url": "https://oceanservice.noaa.gov/education/tutorial_corals/",
        "hashtags": ["#ManaTechTelugu", "#CoralReefs", "#OceanLife", "#MarineScience", "#Nature"],
    },
    {
        "slug": "monarch-butterfly-migration", "category": "WILDLIFE",
        "title": "వేల కిలోమీటర్లు ప్రయాణించే సీతాకోకచిలుక!",
        "description": "మోనార్క్ సీతాకోకచిలుకలు ఉత్తర అమెరికాలోని ప్రాంతాల నుంచి మెక్సికోలోని శీతాకాల నివాస ప్రాంతాలకు దీర్ఘదూర వలస ప్రయాణం చేస్తాయి. ఈ ప్రయాణంలో అనేక తరాల సీతాకోకచిలుకలు భాగమవుతాయి.",
        "cta": "ఇంత చిన్న జీవి చేసే ప్రయాణం ఆశ్చర్యంగా ఉందా?",
        "source_title": "Monarch Butterfly — U.S. Fish & Wildlife Service",
        "source_url": "https://www.fws.gov/species/monarch-butterfly-danaus-plexippus",
        "hashtags": ["#ManaTechTelugu", "#MonarchButterfly", "#Migration", "#Wildlife", "#NatureFacts"],
    },
    {
        "slug": "saturn-rings", "category": "PLANETARY SCIENCE",
        "title": "మంచు ముక్కలతో ఏర్పడిన గ్రహపు వలయాలు!",
        "description": "శని గ్రహపు వలయాలు అనేక చిన్న మంచు, రాతి ముక్కలతో ఏర్పడ్డాయి. అవి గ్రహం చుట్టూ వేర్వేరు కక్ష్యల్లో తిరుగుతూ విస్తారమైన వలయాల్లా కనిపిస్తాయి.",
        "cta": "శని వలయాలను దగ్గరగా చూడగలిగితే ఎలా ఉంటుంది?",
        "source_title": "Saturn — NASA Science",
        "source_url": "https://science.nasa.gov/saturn/",
        "hashtags": ["#ManaTechTelugu", "#Saturn", "#PlanetScience", "#NASA", "#SpaceFacts"],
    },
    {
        "slug": "tardigrade", "category": "MICRO WORLD",
        "title": "అతి చిన్నదైనా అద్భుతమైన జీవి!",
        "description": "టార్డిగ్రేడ్‌లు సూక్ష్మ పరిమాణం గల ఎనిమిది కాళ్ల జీవులు. కొన్ని జాతులు అననుకూల పరిస్థితుల్లో తమ జీవక్రియను తీవ్రంగా తగ్గించి తాత్కాలికంగా తట్టుకునే స్థితిలోకి వెళ్లగలవు.",
        "cta": "ఇంత చిన్న జీవి గురించి ముందెప్పుడైనా విన్నారా?",
        "source_title": "Tardigrades — NASA Astrobiology",
        "source_url": "https://astrobiology.nasa.gov/",
        "hashtags": ["#ManaTechTelugu", "#Tardigrade", "#MicroWorld", "#Biology", "#ScienceFacts"],
    },
]


def select_topic(post_date: date) -> dict:
    """Rotate through curated non-temple topics without adjacent repeats."""
    day_index = (post_date - BASE_DATE).days
    return TOPIC_ROTATION[day_index % len(TOPIC_ROTATION)]


def slide_copy(topic: dict) -> list[tuple[str, str]]:
    parts = [part.strip() for part in topic["description"].replace("।", ".").split(".") if part.strip()]
    facts = (parts + [topic["cta"], topic["description"]])[:3]
    return [
        (topic["title"], facts[0]),
        ("ఇంకో ఆసక్తికర విషయం", facts[1]),
        ("ఇది ఎందుకు ప్రత్యేకం?", facts[2]),
        ("మీ అభిప్రాయం?", topic["cta"]),
    ]


def make_prompt(topic: dict, slide_number: int, heading: str = "", body: str = "") -> str:
    subject = topic["slug"].replace("-", " ")
    directions = (
        "an expansive cinematic hero shot with one unmistakable focal subject",
        "a lively environmental scene showing the subject in its natural setting",
        "an intricate macro close-up revealing vivid texture, colour and fine detail",
        "a surprising dynamic angle with rich depth and a visually memorable moment",
    )
    return (
        f"Create a stunning premium photorealistic cinematic image about {subject}. "
        f"Image {slide_number} of a four-image Instagram carousel. "
        f"Visual direction: {directions[slide_number - 1]}. "
        f"Factual context: {topic['description']} "
        "Use vibrant natural colours, beautiful lighting, realistic materials, rich detail, "
        "strong composition and an immersive environment. Make the subject large, clear and "
        "visually compelling; fill the entire frame with the scene. Portrait 4:5, 1080x1350. "
        "ABSOLUTELY NO text, letters, words, numbers, captions, typography, titles, labels, "
        "logos, watermarks, borders, frames, panels, boxes, banners, text gradients, graphic "
        "design, infographic, poster layout, UI, or empty space reserved for text. "
        "The output must be a clean standalone photograph/artistic visual only."
    )


def render_clean_image(base_bytes: bytes, output_path: Path) -> None:
    """Save AI artwork only; never draw text, panels or graphic overlays."""
    from io import BytesIO

    with Image.open(BytesIO(base_bytes)) as source:
        image = ImageOps.fit(
            source.convert("RGB"), (1080, 1350),
            method=Image.Resampling.LANCZOS, centering=(0.5, 0.5),
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "JPEG", quality=94, optimize=True, progressive=True)
    if output_path.stat().st_size > 8 * 1024 * 1024:
        raise RuntimeError(f"Instagram carousel image exceeds 8 MB: {output_path.name}")
    with Image.open(output_path) as check:
        if check.size != (1080, 1350):
            raise RuntimeError(f"Unexpected carousel image dimensions: {check.size}")
        check.verify()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Publishing date YYYY-MM-DD")
    args = parser.parse_args()
    post_date = date.fromisoformat(args.date)
    date_text = post_date.isoformat()

    feed_manifest = ROOT / "posts" / f"{date_text}.json"
    feed_dir = ROOT / "posts" / "images" / date_text
    story_manifest = ROOT / "stories" / f"{date_text}.json"
    story_image = ROOT / "stories" / "images" / date_text / "story-01.jpg"
    if any(p.exists() for p in (feed_manifest, feed_dir, story_manifest, story_image)):
        raise RuntimeError(f"Assets already exist for {date_text}; refusing to overwrite or risk duplicate publishing.")

    topic = select_topic(post_date)
    print(f"Selected topic: {topic['slug']} — {topic['title']}")
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not account_id or not token:
        raise RuntimeError("Cloudflare account/token GitHub Actions secrets are missing.")
    slide_text = slide_copy(topic)

    with tempfile.TemporaryDirectory(prefix="mana-tech-ai-") as tmp:
        temp_dir = Path(tmp)
        image_urls: list[str] = []
        for number, (heading, body) in enumerate(slide_text, start=1):
            print(f"Generating clean photo-only image {number}/{FEED_SLIDES}...")
            generated = cloudflare_generate(
                make_prompt(topic, number, heading, body), account_id, token
            )
            output = feed_dir / f"post-{number:02d}.jpg"
            render_clean_image(generated, output)
            image_urls.append(
                RAW_PREFIX + f"posts/images/{date_text}/post-{number:02d}.jpg"
            )

        # Keep the existing Story workflow independent: one dedicated AI Story image.
        print("Generating the separate Story image...")
        story_bytes = cloudflare_generate(
            "Create a vibrant cinematic vertical 9:16 photorealistic image about "
            + topic["slug"].replace("-", " ")
            + ". Fill the frame with a colourful scene and clear focal subject. "
              "No text, letters, captions, logos, watermarks, panels, boxes, borders, "
              "poster design, infographic or graphic overlays. Clean image only.",
            account_id, token,
        )
        story_dir = temp_dir / "story"
        save_variants(story_bytes, story_dir)
        story_image.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(story_dir / "story-9x16.jpg", story_image)

    ai_note = "చిత్రాలు AI ద్వారా రూపొందించిన కళాత్మక దృశ్యాలు; సమాచార వివరాలకు మూలాన్ని చూడండి."
    feed_post = {
        "id": f"{date_text}-01",
        "status": "staged",
        "topic": topic["slug"],
        "language": "te",
        "title": topic["title"],
        "description": topic["description"],
        "call_to_action": topic["cta"],
        "hashtags": topic["hashtags"],
        "image_url": image_urls[0],
        "image_urls": image_urls,
        "alt_text": f"Four-image photo-only carousel about {topic['slug'].replace('-', ' ')} in India.",
        "is_factual": True,
        "sources": [{
            "title": topic["source_title"],
            "url": topic["source_url"],
            "checked_at": date_text,
        }],
        "image_origin": "Four clean Cloudflare Workers AI generated images with no text or graphic overlays",
        "image_disclaimer": ai_note,
        "carousel_slide_count": FEED_SLIDES,
    }
    feed_manifest.parent.mkdir(parents=True, exist_ok=True)
    feed_manifest.write_text(
        json.dumps({"date": date_text, "posts": [feed_post]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    story = {
        "id": f"{date_text}-story-01",
        "status": "queued",
        "topic": topic["slug"],
        "title": topic["title"],
        "image_url": f"https://raw.githubusercontent.com/{REPO}/main/stories/images/{date_text}/story-01.jpg",
        "alt_text": f"AI-generated artistic Story image about {topic['slug'].replace('-', ' ')} in India.",
        "image_origin": "Cloudflare Workers AI generated photo-only Story image",
        "image_disclaimer": ai_note,
    }
    story_manifest.parent.mkdir(parents=True, exist_ok=True)
    story_manifest.write_text(
        json.dumps({"date": date_text, "stories": [story]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for path in [*(feed_dir / f"post-{i:02d}.jpg" for i in range(1, FEED_SLIDES + 1)), story_image]:
        if not path.is_file() or path.stat().st_size < 10_000:
            raise RuntimeError(f"Generated image is missing or too small: {path}")
        with path.open("rb") as handle:
            if handle.read(3) != b"\xff\xd8\xff":
                raise RuntimeError(f"Generated asset is not a JPEG: {path}")

    print(f"Prepared {FEED_SLIDES} Feed carousel slides under {feed_dir}")
    print(f"Prepared separate Story image: {story_image}")
    print(f"Prepared Feed manifest: {feed_manifest}")
    print(f"Prepared Story manifest: {story_manifest}")
    print("Assets are staged only; no Instagram or Facebook post was published.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Cloudflare daily post preparation failed safely: {exc}", file=sys.stderr)
        raise SystemExit(1)
