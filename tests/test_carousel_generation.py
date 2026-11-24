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
    def test_four_distinct_slide_copy_blocks(self):
        topic = TOPICS[((date(2026, 11, 24) - generator.BASE_DATE).days * 5) % len(TOPICS)]
        blocks = generator.slide_copy(topic)
        self.assertEqual(len(blocks), 4)
        self.assertTrue(all(heading and body for heading, body in blocks))
        prompts = [
            generator.make_prompt(topic, index, heading, body)
            for index, (heading, body) in enumerate(blocks, start=1)
        ]
        self.assertEqual(len(set(prompts)), 4)

    def test_topic_rotation_includes_non_temple_topics(self):
        categories = {item["category"] for item in TOPICS}
        self.assertIn("SPACE SCIENCE", categories)
        self.assertIn("OCEAN SCIENCE", categories)
        self.assertIn("ANIMAL FACTS", categories)

    def test_rendered_slide_is_valid_feed_jpeg(self):
        font_path = generator.find_telugu_font()
        source = BytesIO()
        Image.new("RGB", (1080, 1920), (45, 85, 125)).save(source, format="JPEG")
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "post-01.jpg"
            generator.render_infographic(
                source.getvalue(), output, TOPICS[0], 1,
                "తెలుగు శీర్షిక", "ఇది ఒక పరీక్ష వివరణ.", font_path,
            )
            with Image.open(output) as image:
                self.assertEqual(image.size, (1080, 1350))
                self.assertEqual(image.format, "JPEG")
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
