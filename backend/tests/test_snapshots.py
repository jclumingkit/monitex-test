from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.snapshots import router
from snapshot_storage import get_snapshot_path, save_frame_snapshot


class SnapshotStorageTests(unittest.TestCase):
    def test_saves_jpeg_with_generated_snapshot_id(self):
        frame = object()

        def write_image(path, received_frame):
            self.assertIs(received_frame, frame)
            Path(path).write_bytes(b"jpeg-data")
            return True

        with (
            TemporaryDirectory() as temporary_directory,
            patch("snapshot_storage.SNAPSHOT_DIR", Path(temporary_directory)),
            patch("snapshot_storage.cv2.imwrite", side_effect=write_image),
        ):
            snapshot_id = save_frame_snapshot(frame)
            snapshot_path = get_snapshot_path(snapshot_id or "")

            self.assertIsNotNone(snapshot_path)
            self.assertEqual(snapshot_path.read_bytes(), b"jpeg-data")

    def test_rejects_unsafe_snapshot_id(self):
        self.assertIsNone(get_snapshot_path("../secret"))


class SnapshotApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_serves_snapshot_as_jpeg(self):
        snapshot_id = "0123456789abcdef0123456789abcdef"

        with (
            TemporaryDirectory() as temporary_directory,
            patch("snapshot_storage.SNAPSHOT_DIR", Path(temporary_directory)),
        ):
            snapshot_path = Path(temporary_directory) / f"{snapshot_id}.jpg"
            snapshot_path.write_bytes(b"jpeg-data")

            response = self.client.get(f"/api/snapshots/{snapshot_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"jpeg-data")
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertEqual(
            response.headers["cache-control"],
            "public, max-age=31536000, immutable",
        )

    def test_returns_not_found_for_invalid_snapshot_id(self):
        response = self.client.get("/api/snapshots/not-a-snapshot")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
