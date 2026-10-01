from pathlib import Path

from ultralytics import YOLO


WORKER_DIR = Path(__file__).resolve().parent
VIDEO_PATH = WORKER_DIR / "test_video.mp4"
MODEL_PATH = WORKER_DIR / "yolo26n.pt"
PERSON_CLASS_ID = 0


def main() -> None:
    model = YOLO(str(MODEL_PATH))
    model.track(
        source=str(VIDEO_PATH),
        show=True,
        classes=[PERSON_CLASS_ID],
    )


if __name__ == "__main__":
    main()
