"""START KEYBIND."""

START_KEYBIND = r'ctrl+shift+a' # What buttons need to be held to start the photogrammetry program.

"""Path variables."""

VIDEO_DIR_PATH = r'C:\Users\ROV\Cockpit\videos' # Directory of the folder that holds the videos
IMAGE_DIR_PATH = r'ROV\photo\Photogrammetry\ImageFolder' # Directory of Folder with all of the images.
OUTPUT_DIR_PATH = r'ROV\photo\Photogrammetry\Output' # Directory where the output will be found.

"""Number of images (+1) for extract_frames."""

NUM_IMAGES = 20

"""Tunable constants for create_3D_reconstruction in photogrammetry.py."""

# --- SIFT feature extraction ---
SIFT_MAX_IMAGE_SIZE = 1000
SIFT_MAX_NUM_FEATURES = 4096

# --- Incremental mapper thresholds ---
# Loosened for video-derived frames with low parallax.
INIT_MIN_TRI_ANGLE = 4.0       # default 16 is too strict for low-parallax video
INIT_MAX_FORWARD_MOTION = 1.0
FILTER_MIN_TRI_ANGLE = 1.0
TRIANGULATION_MIN_ANGLE = 1.0
MIN_NUM_MATCHES = 15

# --- Bundle adjustment ---
# Hard caps so the final global BA cannot run away on CPU.
BA_GLOBAL_MAX_NUM_ITERATIONS = 10
BA_GLOBAL_MAX_REFINEMENTS = 1
BA_GLOBAL_FUNCTION_TOLERANCE = 1e-4
BA_GLOBAL_MAX_REFINEMENT_CHANGE = 1e-3
BA_LOCAL_MAX_NUM_ITERATIONS = 10
BA_LOCAL_MAX_REFINEMENTS = 1
BA_GLOBAL_FRAMES_FREQ = 1000
MAPPER_NUM_THREADS = -1
MAPPER_MULTIPLE_MODELS = False
MAPPER_MAX_NUM_MODELS = 1

# --- Snapshotting ---
# Periodic on-disk snapshots so a usable model can be recovered if BA aborts.
SNAPSHOT_FRAMES_FREQ = 20

# --- PatchMatch dense stereo ---
PMS_NUM_ITERATIONS = 2
PMS_WINDOW_STEP = 2
PMS_GEOM_CONSISTENCY = False
PMS_MAX_IMAGE_SIZE = 1000
PMS_GPU_INDEX = "0"

# --- Stereo fusion ---
# Relaxed because window_step >= 2 leaves sparse depth maps; default
# min_num_pixels=5 would discard nearly every fused point.
FUSION_MIN_NUM_PIXELS = 2
FUSION_MAX_REPROJ_ERROR = 4.0
FUSION_MAX_NORMAL_ERROR = 20.0
FUSION_INPUT_TYPE = "photometric"  # patch_match runs with geom_consistency=False