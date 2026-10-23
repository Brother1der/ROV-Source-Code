import argparse
from pathlib import Path
import cv2
from ultralytics import YOLO
import glob
import os


CONFIDENCE_LEVEL = 0.5
"""
Gets the invasive count based off the ID of the invasive species
"""
def getInvasiveCount(invasive_class_id, results):
    invasive_count = 0
    if invasive_class_id is not None and results[0].boxes is not None:
        invasive_count = int((results[0].boxes.cls == invasive_class_id).sum())
    
    return invasive_count


"""
Main loop that IDs the crabs and builds the video feed
"""
def process(cap, model):
    invasive_class_id = next(
        (i for i, n in model.names.items() if n == "european_green_crab"), None
    )
        
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        results = model(frame, conf=CONFIDENCE_LEVEL, verbose=False)
        annotated = results[0].plot()

        #Getting the count of the number of invasive crabs in the frame(European Green Crabs)
        #Boxes are the boxes in video feed(Duh)
        invasive_count = getInvasiveCount(invasive_class_id, results)

        #Constants for the video feed
        text = f"European Green Crab Count: {invasive_count}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 1.5
        thickness = 5

        #Writing the top header to the top of the screen.
        (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
        x = (annotated.shape[1] - tw) // 2
        y = th + 20
        cv2.rectangle(annotated, (0, 0), (annotated.shape[1], y + 20), (105,94,2), -1)
        cv2.putText(annotated, text, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)

        #Quit via Q instead if needed
        cv2.imshow("YOLO test (q to quit)", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    
def get_latest_file(dir_path):
    try:
        list_of_files = glob.glob(os.path.join(dir_path, '*.mp4'))  # Get list of all mp4 files in directory
        if not list_of_files:
            return None  # Return None if directory is empty
        latest_file = max(list_of_files, key=os.path.getmtime)  # Get file with the latest modification time
        return latest_file
    except OSError as e:
         print(f"Error accessing directory: {e}")
         return None

"""
Prepare the file for processing so we can run the program
"""
def prepare():
  parser = argparse.ArgumentParser(description="Run a YOLO model on a video.")
  parser.add_argument("--video", default=r"C:\Users\ROV\Cockpit\videos\CrabTest.mp4")
  parser.add_argument(
        "--weights",
        default="runs/detect/crab-3/weights/best.pt",
        help="Path to weights. Falls back to yolov8n.pt if missing.",
  )
  parser.add_argument("--conf", type=float, default=0.5)
  args = parser.parse_args()
  weights = args.weights if Path(args.weights).exists() else "yolo11n.pt"
  print(f"Using video:   {args.video}")
  model = YOLO(weights)
  cap = cv2.VideoCapture(args.video)
  if not cap.isOpened():
    raise SystemExit(f"Could not open video: {args.video}")
  
  return cap,model

"""
Main Loop that runs the video through the object detection model and plays video after
"""
def main():
    cap,model = prepare()
    process(cap, model)
    cap.release()
    cv2.destroyAllWindows()


#Entry point
if __name__ == "__main__":
    main()
