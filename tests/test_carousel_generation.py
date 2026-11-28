import tempfile
import unittest
from datetime import date
from pathlib import Path
from io import BytesIO

from PIL import Image

import prepare_cloudflare_post as generator
import publish
from commons_poster import TOPICS


class CarouselGenerationTests(unittest.TestCase):
    def test_four_unique_photo_only_prompts(self):
        topic = TOPICS[(date(2026, 11, 24) - generator.BASE_DATE).days % len(TOPICS)]
        prompts = [generator.make_prompt(topic, index) for index in range(1, 5)]
        self.assertEqual(len(set(prompts)), 4)
        self.assertTrue(all("no text" in prompt.lower() for prompt in prompts))
        self.assertTrue(all("text boxes" in prompt.lower() for prompt in prompts))

    def test_topic_rotation_excludes_temple_repetition(self):
        categories = {item["category"] for item in TOPICS}
        self.assertGreaterEqual(len(TOPICS), 12)
        self.assertTrue(all("TEMPLE" not in category and "HERITAGE" not in category for category in categories))
        self.assertIn("COLORFUL CREATURES", categories)
        self.assertIn("ANIMAL LIFESTYLE", categories)
        self.assertIn("SPACE SCIENCE", categories)

    def test_photo_only_slide_is_valid_feed_jpeg(self):
        source = BytesIO()
        Image.new("RGB", (1080, 1920), (45, 85, 125)).save(source, format="JPEG")
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "post-01.jpg"
            generator.save_photo_only(source.getvalue(), output)
            self.assertGreater(output.stat().st_size, 0)
            with Image.open(output) as image:
                self.assertEqual(image.size, (1080, 1350))
                self.assertEqual(image.format, "JPEG")
                image.verify()

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
            "alt_text": "Four-slide Telugu infographic test.",
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
