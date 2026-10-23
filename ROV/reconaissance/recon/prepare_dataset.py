import argparse
import json
import random
import shutil
from pathlib import Path


CLASS_MAP = {
    "Native Crab": "native_crab",
    "European Green Crab": "european_green_crab",
    "European Green Crab3": "european_green_crab",
    "Claw": "claw",
    "Lane Marker": "lane_marker",
    "Pool Vent": "pool_vent",
    "Servo Motor": "servo_motor",
}

YOLO_CLASS_ORDER = [
    "native_crab",
    "european_green_crab",
    "claw",
    "lane_marker",
    "pool_vent",
    "servo_motor",
]


def coco_to_yolo_box(bbox, img_w, img_h):
    x, y, w, h = (float(v) for v in bbox)
    img_w = float(img_w)
    img_h = float(img_h)
    cx = (x + w / 2) / img_w
    cy = (y + h / 2) / img_h
    return cx, cy, w / img_w, h / img_h


def prepare(coco_dir: Path, out_dir: Path, val_frac: float, seed: int) -> None:
    json_path = coco_dir / "_annotations.coco.json"
    data = json.loads(json_path.read_text())

    cat_id_to_yolo = {}
    for cat in data["categories"]:
        if cat["name"] in CLASS_MAP:
            cat_id_to_yolo[cat["id"]] = YOLO_CLASS_ORDER.index(CLASS_MAP[cat["name"]])

    img_id_to_meta = {img["id"]: img for img in data["images"]}
    anns_per_img: dict[int, list] = {img["id"]: [] for img in data["images"]}
    for ann in data["annotations"]:
        if ann["category_id"] not in cat_id_to_yolo:
            continue
        anns_per_img[ann["image_id"]].append(ann)

    image_ids = list(img_id_to_meta.keys())
    random.Random(seed).shuffle(image_ids)
    n_val = max(1, int(len(image_ids) * val_frac))
    val_ids = set(image_ids[:n_val])

    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    for img_id, meta in img_id_to_meta.items():
        split = "val" if img_id in val_ids else "train"
        src_img = coco_dir / meta["file_name"]
        dst_img = out_dir / "images" / split / meta["file_name"]
        shutil.copy2(src_img, dst_img)

        label_lines = []
        for ann in anns_per_img[img_id]:
            cls = cat_id_to_yolo[ann["category_id"]]
            cx, cy, bw, bh = coco_to_yolo_box(ann["bbox"], meta["width"], meta["height"])
            label_lines.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

        label_path = out_dir / "labels" / split / (Path(meta["file_name"]).stem + ".txt")
        label_path.write_text("\n".join(label_lines))

    print(f"Wrote {len(image_ids) - n_val} train / {n_val} val to {out_dir}")
    print(f"Classes: {YOLO_CLASS_ORDER}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Roboflow COCO export → YOLO format with train/val split.")
    parser.add_argument("--coco", default=r"C:\Users\ROV\Downloads\Crabs V2.coco\train", help="Folder with images + _annotations.coco.json")
    parser.add_argument("--out", default="dataset", help="YOLO dataset root")
    parser.add_argument("--val", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    prepare(Path(args.coco), Path(args.out), args.val, args.seed)
