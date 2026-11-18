import unittest
from datetime import datetime, timezone

from firestore_scheduler import SchedulerError, build_caption, parse_local_schedule, validate_post


class ScheduleTests(unittest.TestCase):
    def test_ist_schedule_not_due_before_selected_time(self):
        settings = {"postTime": "18:00", "timeZone": "Asia/Kolkata", "startDate": "2026-11-18"}
        now = datetime(2026, 11, 18, 12, 25, tzinfo=timezone.utc)  # 17:55 IST
        _, local_day, due = parse_local_schedule(settings, now)
        self.assertEqual(local_day, "2026-11-18")
        self.assertFalse(due)

    def test_ist_schedule_due_at_selected_time(self):
        settings = {"postTime": "18:00", "timeZone": "Asia/Kolkata", "startDate": "2026-11-18"}
        now = datetime(2026, 11, 18, 12, 30, tzinfo=timezone.utc)  # 18:00 IST
        _, _, due = parse_local_schedule(settings, now)
        self.assertTrue(due)

    def test_start_date_blocks_early_runs(self):
        settings = {"postTime": "09:00", "timeZone": "Asia/Kolkata", "startDate": "2026-11-19"}
        now = datetime(2026, 11, 18, 10, 0, tzinfo=timezone.utc)
        _, _, due = parse_local_schedule(settings, now)
        self.assertFalse(due)

    def test_invalid_timezone_rejected(self):
        with self.assertRaises(SchedulerError):
            parse_local_schedule({"postTime": "09:00", "timeZone": "Not/AZone"}, datetime.now(timezone.utc))


class CaptionTests(unittest.TestCase):
    def test_caption_and_hashtags(self):
        post = {"id": "p1", "title": "Temple Mystery", "caption": "A fascinating detail.", "hashtags": ["#History", "India"]}
        self.assertEqual(build_caption(post), "Temple Mystery\n\nA fascinating detail.\n\n#History #India")

    def test_caption_length_checked(self):
        post = {"id": "p2", "title": "T", "caption": "x" * 2200, "hashtags": []}
        with self.assertRaises(SchedulerError):
            build_caption(post)

    def test_https_image_required(self):
        with self.assertRaises(SchedulerError):
            validate_post({"id": "p3", "imageUrl": "http://example.com/a.jpg", "title": "T", "caption": "C"})


if __name__ == "__main__":
    unittest.main()
