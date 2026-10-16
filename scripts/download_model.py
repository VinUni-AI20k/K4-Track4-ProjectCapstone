"""Tải model Face Landmarker bản float16/1 từ kho chính thức của Google."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import urllib.request


MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)
DEFAULT_PATH = Path(__file__).resolve().parents[1] / "models" / "face_landmarker.task"
MODEL_SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"File đã tồn tại: {args.output}; không ghi đè tự động")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".task.part")
    try:
        with urllib.request.urlopen(MODEL_URL, timeout=60) as response:
            with temporary.open("wb") as target:
                while chunk := response.read(1024 * 1024):
                    target.write(chunk)
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        if digest != MODEL_SHA256:
            raise ValueError("SHA256 model không khớp bản đã kiểm tra; không sử dụng file tải về")
        temporary.replace(args.output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(f"Model: {args.output}")
    print(f"SHA256: {hashlib.sha256(args.output.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
