import argparse
import random
import shutil
from pathlib import Path


def split(raw_dir: Path, dataset_dir: Path, val_frac: float, seed: int) -> None:
    images = sorted(p for p in raw_dir.glob("*.jpg"))
    if not images:
        raise SystemExit(f"No .jpg files found in {raw_dir}")

    paired = [p for p in images if p.with_suffix(".txt").exists()]
    skipped = len(images) - len(paired)
    if not paired:
        raise SystemExit(
            f"None of the {len(images)} images in {raw_dir} have a matching .txt label file. "
            "Label them first (LabelImg in YOLO mode saves a .txt next to each image)."
        )

    random.Random(seed).shuffle(paired)
    n_val = max(1, int(len(paired) * val_frac))
    val_set = set(paired[:n_val])

    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        (dataset_dir / sub).mkdir(parents=True, exist_ok=True)

    for img in paired:
        split_name = "val" if img in val_set else "train"
        shutil.copy2(img, dataset_dir / "images" / split_name / img.name)
        shutil.copy2(img.with_suffix(".txt"), dataset_dir / "labels" / split_name / (img.stem + ".txt"))

    print(f"Split {len(paired)} labeled images: {len(paired) - n_val} train / {n_val} val")
    if skipped:
        print(f"Skipped {skipped} unlabeled images")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split labeled frames into YOLO train/val folders.")
    parser.add_argument("--raw", default="dataset/raw", help="Folder with images + YOLO .txt labels")
    parser.add_argument("--dataset", default="dataset", help="Root dataset folder")
    parser.add_argument("--val", type=float, default=0.2, help="Fraction held out for validation")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    split(Path(args.raw), Path(args.dataset), args.val, args.seed)
