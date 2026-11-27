import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from io import BytesIO

from PIL import Image

import prepare_cloudflare_post as generator
import publish


class CarouselGenerationTests(unittest.TestCase):
    def test_four_distinct_photo_prompts(self):
        topic = generator.select_topic(date(2026, 11, 27))
        blocks = generator.slide_copy(topic)
        self.assertEqual(len(blocks), 4)
        prompts = [
            generator.make_prompt(topic, index, heading, body)
            for index, (heading, body) in enumerate(blocks, start=1)
        ]
        self.assertEqual(len(set(prompts)), 4)

    def test_topic_rotation_avoids_heritage_and_temple_categories(self):
        selected = [
            generator.select_topic(date(2026, 11, 17) + timedelta(days=offset))
            for offset in range(len(generator.TOPIC_ROTATION))
        ]
        self.assertEqual(len({item["slug"] for item in selected}), len(generator.TOPIC_ROTATION))
        for item in selected:
            combined = (item["slug"] + " " + item["category"]).casefold()
            self.assertNotIn("temple", combined)
            self.assertNotIn("heritage", combined)
            self.assertNotIn("architecture", combined)

    def test_prompt_forbids_all_text_and_graphic_overlays(self):
        prompt = generator.make_prompt(generator.TOPIC_ROTATION[0], 1)
        self.assertIn("ABSOLUTELY NO text", prompt)
        self.assertIn("panels, boxes, banners", prompt)
        self.assertIn("clean standalone", prompt)
        self.assertNotIn("space near the lower quarter", prompt)

    def test_rendered_slide_is_clean_feed_jpeg(self):
        source = BytesIO()
        Image.new("RGB", (1080, 1920), (45, 85, 125)).save(source, format="JPEG")
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "post-01.jpg"
            generator.render_clean_image(source.getvalue(), output)
            with Image.open(output) as image:
                self.assertEqual(image.size, (1080, 1350))
                self.assertEqual(image.format, "JPEG")
                self.assertEqual(image.getpixel((540, 1200)), (45, 85, 125))
            self.assertGreater(output.stat().st_size, 10_000)

    def test_publisher_accepts_four_image_carousel_manifest(self):
        urls = [
            "https://raw.githubusercontent.com/trinadharaomamidi97-spec/mana-tech-autopilot/main/posts/images/2026-11-24/post-01.jpg",
            "https://raw.githubusercontent.com/trinadharaomamidi97-spec/mana-tech-autopilot/main/posts/images/2026-11-24/post-02.jpg",
            "https://raw.githubusercontent.com/trinadharaomamidi97-spec/mana-tech-autopilot/main/posts/images/2026-11-24/post-03.jpg",
            "https://raw.githubusercontent.com/trinadharaomamidi97-spec/mana-tech-autopilot/main/posts/images/2026-11-24/post-04.jpg",
        ]
        post = {
            "id": "2026-11-24-01",
            "status": "queued",
            "topic": "test-topic",
            "language": "te",
            "title": "పరీక్ష శీర్షిక",
            "description": "పరీక్ష వివరణ.",
            "image_url": urls[0],
            "image_urls": urls,
            "alt_text": "Four-image photo-only carousel test.",
            "hashtags": ["#ManaTechTelugu", "#TeluguFacts"],
            "is_factual": True,
            "sources": [{
                "title": "Test source",
                "url": "https://example.org/fact",
                "checked_at": "2026-11-24",
            }],
        }
        publish.validate_post(post)
        self.assertEqual(len(post["image_urls"]), 4)


if __name__ == "__main__":
    unittest.main()
