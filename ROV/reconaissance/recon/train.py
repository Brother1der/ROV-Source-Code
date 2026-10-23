import argparse

import torch
from ultralytics import YOLO


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune YOLO11 on the crab dataset.")
    parser.add_argument("--data", default="crabs.yaml")
    parser.add_argument("--model", default="yolo11n.pt", help="Base weights to fine-tune from")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--name", default="crab", help="Run name under runs/detect/")
    args = parser.parse_args()

    print(f"Training on device: {args.device}")
    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        name=args.name,
    )


if __name__ == "__main__":
    main()
