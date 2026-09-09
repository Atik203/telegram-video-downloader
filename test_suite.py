"""
Comprehensive Unit Tests for Telegram Video Downloader
"""

import unittest
import os
from pathlib import Path

import config
from link_parser import parse_telegram_link, extract_targets_from_text, normalize_private_channel_id
from downloader_engine import sanitize_filename, DownloaderEngine
from client_manager import VideoInfo
import ui


class TestLinkParser(unittest.TestCase):
    def test_single_private_link(self):
        url = "https://t.me/c/3100538760/15"
        target = parse_telegram_link(url)
        self.assertIsNotNone(target)
        self.assertTrue(target.is_private)
        self.assertEqual(target.channel_ref, -1003100538760)
        self.assertEqual(target.raw_channel_id, 3100538760)
        self.assertEqual(target.message_ids, [15])

    def test_private_link_with_query_params(self):
        url = "https://t.me/c/3100538760/15?single"
        target = parse_telegram_link(url)
        self.assertIsNotNone(target)
        self.assertEqual(target.channel_ref, -1003100538760)
        self.assertEqual(target.message_ids, [15])

    def test_range_private_link(self):
        url = "https://t.me/c/3100538760/15-20"
        target = parse_telegram_link(url)
        self.assertIsNotNone(target)
        self.assertEqual(target.channel_ref, -1003100538760)
        self.assertEqual(target.message_ids, [15, 16, 17, 18, 19, 20])

    def test_topic_private_link(self):
        url = "https://t.me/c/3100538760/2/15"
        target = parse_telegram_link(url)
        self.assertIsNotNone(target)
        self.assertEqual(target.channel_ref, -1003100538760)
        self.assertEqual(target.message_ids, [15])

    def test_public_link(self):
        url = "https://t.me/telegram_channel/99"
        target = parse_telegram_link(url)
        self.assertIsNotNone(target)
        self.assertFalse(target.is_private)
        self.assertEqual(target.channel_ref, "telegram_channel")
        self.assertEqual(target.message_ids, [99])

    def test_extract_targets_from_text(self):
        text = """
        Check these out:
        https://t.me/c/3100538760/15
        https://t.me/c/3100538760/16-18
        and also https://t.me/somechannel/50
        """
        targets = extract_targets_from_text(text)
        self.assertEqual(len(targets), 3)
        self.assertEqual(targets[0].message_ids, [15])
        self.assertEqual(targets[1].message_ids, [16, 17, 18])
        self.assertEqual(targets[2].channel_ref, "somechannel")


class TestSanitizeFilename(unittest.TestCase):
    def test_windows_forbidden_chars(self):
        dirty = 'My:Video?*<Cool>|"File"/Name.mp4'
        clean = sanitize_filename(dirty)
        for char in '<>:"/\\|?*':
            self.assertNotIn(char, clean)
        self.assertTrue(clean.endswith(".mp4"))

    def test_empty_filename(self):
        clean = sanitize_filename("   ")
        self.assertEqual(clean, "telegram_video.mp4")

    def test_double_extension_cleaning(self):
        dirty = "video_7595242697644835660.mp4.mp4"
        clean = sanitize_filename(dirty)
        self.assertEqual(clean, "video_7595242697644835660.mp4")


class TestUIFormatters(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(ui.format_bytes(1024), "1.00 KB")
        self.assertEqual(ui.format_bytes(1024 * 1024 * 50), "50.00 MB")
        self.assertEqual(ui.format_bytes(1024 * 1024 * 1024 * 2), "2.00 GB")

    def test_format_duration(self):
        self.assertEqual(ui.format_duration(45), "00:45")
        self.assertEqual(ui.format_duration(125), "02:05")
        self.assertEqual(ui.format_duration(124.58), "02:05")
        self.assertEqual(ui.format_duration(3665.2), "01:01:05")
        self.assertEqual(ui.format_duration(0.0), "-")


class TestConfig(unittest.TestCase):
    def test_config_validation(self):
        valid, msg = config.validate_config()
        self.assertTrue(valid, f"Config validation failed: {msg}")

    def test_download_dir_drive_root(self):
        p1 = config.parse_download_dir("M:\\")
        self.assertEqual(str(p1), "M:\\")
        p2 = config.parse_download_dir("M:")
        self.assertEqual(str(p2), "M:\\")
        p3 = config.parse_download_dir('"M:\\"')
        self.assertEqual(str(p3), "M:\\")
        p4 = config.parse_download_dir("D:\\Downloads\\Telegram")
        self.assertEqual(str(p4), "D:\\Downloads\\Telegram")
        p5 = config.parse_download_dir("downloads")
        self.assertEqual(str(p5), "downloads")


class TestFastDownload(unittest.TestCase):
    def test_connection_count_scaling(self):
        from fast_download import ParallelTransferrer
        # Small files
        c_small = ParallelTransferrer._get_connection_count(1 * 1024 * 1024)
        self.assertEqual(c_small, 4)
        # Large files
        c_large = ParallelTransferrer._get_connection_count(100 * 1024 * 1024)
        self.assertGreaterEqual(c_large, 16)

    def test_resume_state_format(self):
        import json
        state_path = Path("test_resume.part.json")
        try:
            state_data = {
                "file_size": 1000 * 1024 * 1024,
                "part_size": 512 * 1024,
                "part_count": 2000,
                "completed_parts": list(range(1600)),
            }
            state_path.write_text(json.dumps(state_data), encoding="utf-8")

            # Load back
            loaded = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["file_size"], 1000 * 1024 * 1024)
            self.assertEqual(len(loaded["completed_parts"]), 1600)
            
            # Remaining parts calculation
            completed_set = set(loaded["completed_parts"])
            remaining = [i for i in range(loaded["part_count"]) if i not in completed_set]
            self.assertEqual(len(remaining), 400)
            self.assertEqual(remaining[0], 1600)
        finally:
            if state_path.exists():
                state_path.unlink()

    def test_default_concurrency_10(self):
        self.assertEqual(config.DEFAULT_CONCURRENCY, 10)


class TestNewFeatures(unittest.TestCase):
    def test_channel_subfolder_path(self):
        engine_with_subfolders = DownloaderEngine("test_out", organize_by_channel=True)
        info = VideoInfo(
            message_id=101,
            chat_id=-1001234567,
            chat_title="Python Tutorials: Advanced Course",
            filename="lesson_01.mp4",
            file_size=1024 * 1024,
        )
        dest = engine_with_subfolders.get_dest_path(info)
        # Verify it has channel subfolder and sanitized characters
        self.assertIn("Python Tutorials_ Advanced Course", str(dest))
        self.assertTrue(str(dest).endswith("-1001234567_101_lesson_01.mp4"))

        # When subfolders disabled:
        engine_no_subfolders = DownloaderEngine("test_out", organize_by_channel=False)
        dest_no = engine_no_subfolders.get_dest_path(info)
        self.assertNotIn("Python Tutorials", str(dest_no))
        self.assertTrue(str(dest_no).endswith("-1001234567_101_lesson_01.mp4"))

    def test_save_env_credentials(self):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".env") as f:
            temp_path = f.name

        try:
            config.save_env_credentials(
                api_id=999999,
                api_hash="test_hash_abc",
                phone="+123456789",
                download_dir="X:\\MyDownloads",
                env_path=temp_path,
            )
            content = Path(temp_path).read_text(encoding="utf-8")
            self.assertIn("TG_API_ID=999999", content)
            self.assertIn("TG_API_HASH=test_hash_abc", content)
            self.assertIn("TG_PHONE=+123456789", content)
            self.assertIn("DOWNLOAD_DIR=X:\\MyDownloads", content)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_telegram_manager_has_fetch_videos_from_target(self):
        from client_manager import TelegramManager
        manager = TelegramManager()
        self.assertTrue(hasattr(manager, "fetch_videos_from_target"))
        self.assertTrue(callable(getattr(manager, "fetch_videos_from_target")))


if __name__ == "__main__":
    unittest.main()


