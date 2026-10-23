import argparse
from pathlib import Path

import cv2


def extract(video_path: Path, out_dir: Path, fps_out: float) -> int:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"Could not open video: {video_path}")

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(src_fps / fps_out))
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = video_path.stem

    idx = 0
    saved = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            out_path = out_dir / f"{stem}_{idx:06d}.jpg"
            cv2.imwrite(str(out_path), frame)
            saved += 1
        idx += 1

    cap.release()
    print(f"Read {idx} frames at {src_fps:.2f} fps, saved {saved} to {out_dir}")
    return saved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract frames from a video for labeling.")
    parser.add_argument("--video", default=r"C:\Users\ROV\Cockpit\videos\CrabTest.mp4")
    parser.add_argument("--out", default="dataset/raw", help="Output directory for unlabeled frames")
    parser.add_argument("--fps", type=float, default=1.0, help="Frames per second to extract")
    args = parser.parse_args()

    extract(Path(args.video), Path(args.out), args.fps)
