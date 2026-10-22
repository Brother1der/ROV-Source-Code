from moviepy.video.io.VideoFileClip import VideoFileClip
from meshlib import mrmeshpy as mm
from pathlib import Path
from pymavlink import mavutil
import os
import time
import sys
import shutil
import subprocess
import keyboard
import glob
import numpy as np
import pycolmap
import sys
import reconstruction_constants as rc

'''
GOALS:
- Optimize This. (Shorter time on video. Less features? Lower resolution?)
    - Do we need the patchmap? Would sparse work fine on its own?
        - I could mess around with patch match's settings.
    - How much time does printing contribute to this process? (Likely not much. Some of these take 10 or more seconds.)
        - Reduce amount of iterations?
- Figure out how to utilize GPU (Pycolmap refuses to use it.)
- Are these problems also found on home computer? I installed things differently between these two, so it could be possible.
- Still going through with photogrammetry pipeline because I need something to test the scaling on, but in the future, focus efforts on making this any shorter.
- It needs to run, preferrably under 5 minutes. Might just use sparse.
'''

video_dir_path = rc.VIDEO_DIR_PATH # Directory of the folder that holds the videos.
image_dir_path = rc.IMAGE_DIR_PATH # Directory of Folder with all of the images.
videoFile = None

def start_hotkey(): # Creates the hotkey's function
    delete_folder_contents(image_dir_path)
    delete_folder_contents(rc.OUTPUT_DIR_PATH)
    videoFile = get_latest_file(video_dir_path)  # Get the latest video file
    videoFile = r"{}".format(videoFile) # reason we do the whole .format thingy is so that we can get the raw path of the file, saving headaches and code later
    video = VideoFileClip(videoFile) # Load the video files
    extract_frames(video, image_dir_path) # Calls extraction function
    time.sleep(3) # Wait for 5 seconds so all the frames are saved to be safe.
    create_3D_reconstruction(rc.OUTPUT_DIR_PATH) # creates a 3D reconstruction in the specified folder.
    time.sleep(3)
    create_mesh()


def extract_frames(video, image_dir_path):
    if not os.path.exists(image_dir_path):
        os.makedirs(image_dir_path)

    frame_rate = video.fps
    num_frames = int(video.fps * video.duration)
   
    for i in range(num_frames):
        if i % int(num_frames/rc.NUM_IMAGES) == 0:
            t = i / frame_rate
            frame_filename = f"{int(t*frame_rate)}.png"
            imagepath = os.path.join(image_dir_path, frame_filename)
            video.save_frame(imagepath, t)
            print(f"Saved frame at {t} seconds: {imagepath}")
    video.close()

def get_latest_file(dir_path):
    try:
        list_of_files = glob.glob(os.path.join(dir_path, '*.mp4'))  # Get list of all files in directory
        if not list_of_files:
            return None  # Return None if directory is empty
        latest_file = max(list_of_files, key=os.path.getmtime)  # Get file with the latest modification time
        return latest_file
    except OSError as e:
         print(f"Error accessing directory: {e}")
         return None
    
def delete_folder_contents(dir_path):
    try:
        list_of_files = glob.glob(os.path.join(dir_path, '*'))
        for file_path in list_of_files:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
                print(f"Directory deleted @ {file_path}")
            elif os.path.exists(file_path):
                os.remove(file_path)
                print(f"File deleted @ {file_path}")
    except OSError as e:
         print(f"Error accessing directory: {e}")
         return None

def create_3D_reconstruction(output_folder):
    os.makedirs(output_folder, exist_ok=True)
    mvs_path = os.path.join(output_folder, "mvs")
    database_path = os.path.join(output_folder, "database.db")
    snapshot_path = os.path.join(output_folder, "snapshots")
    os.makedirs(snapshot_path, exist_ok=True)

    # Start from a clean database; stale features from a prior run are the
    # most common cause of incremental_mapping aborting in triangulation.
    if os.path.exists(database_path):
        os.remove(database_path)

    # Force pycolmap's glog to flush INFO-level lines to stderr so we can
    # actually see what mapping is doing during the long BA passes.
    pycolmap.logging.minloglevel = 0
    pycolmap.logging.logtostderr = True
    pycolmap.logging.stderrthreshold = 0

    device = pycolmap.Device.cuda if pycolmap.has_cuda else pycolmap.Device.auto

    sift_options = pycolmap.SiftExtractionOptions()
    sift_options.max_image_size = rc.SIFT_MAX_IMAGE_SIZE
    sift_options.max_num_features = rc.SIFT_MAX_NUM_FEATURES

    pycolmap.extract_features(
        database_path,
        image_dir_path,
        sift_options=sift_options,
        device=device,
    )

    pycolmap.match_exhaustive(
        database_path,
        sift_options=pycolmap.SiftMatchingOptions(),
        matching_options=pycolmap.ExhaustiveMatchingOptions(),
        device=device,
    )

    # Initialize mapper_options from reconstruction_constants.py
    mapper_options = pycolmap.IncrementalPipelineOptions()
    mapper_options.mapper.init_min_tri_angle = rc.INIT_MIN_TRI_ANGLE
    mapper_options.mapper.init_max_forward_motion = rc.INIT_MAX_FORWARD_MOTION
    mapper_options.mapper.filter_min_tri_angle = rc.FILTER_MIN_TRI_ANGLE
    mapper_options.triangulation.min_angle = rc.TRIANGULATION_MIN_ANGLE
    mapper_options.min_num_matches = rc.MIN_NUM_MATCHES
    mapper_options.ba_use_gpu = pycolmap.has_cuda
    mapper_options.ba_gpu_index = "0" if pycolmap.has_cuda else "-1"
    mapper_options.ba_global_max_num_iterations = rc.BA_GLOBAL_MAX_NUM_ITERATIONS
    mapper_options.ba_global_max_refinements = rc.BA_GLOBAL_MAX_REFINEMENTS
    mapper_options.ba_global_function_tolerance = rc.BA_GLOBAL_FUNCTION_TOLERANCE
    mapper_options.ba_global_max_refinement_change = rc.BA_GLOBAL_MAX_REFINEMENT_CHANGE
    mapper_options.ba_local_max_num_iterations = rc.BA_LOCAL_MAX_NUM_ITERATIONS
    mapper_options.ba_local_max_refinements = rc.BA_LOCAL_MAX_REFINEMENTS
    mapper_options.ba_global_frames_freq = rc.BA_GLOBAL_FRAMES_FREQ
    mapper_options.num_threads = rc.MAPPER_NUM_THREADS
    mapper_options.multiple_models = rc.MAPPER_MULTIPLE_MODELS
    mapper_options.max_num_models = rc.MAPPER_MAX_NUM_MODELS
    mapper_options.snapshot_path = snapshot_path
    mapper_options.snapshot_frames_freq = rc.SNAPSHOT_FRAMES_FREQ

    registered = [0]
    start_ts = time.time()

    def on_next_image():
        registered[0] += 1
        elapsed = time.time() - start_ts
        print(
            f"[mapper] registered image #{registered[0]} "
            f"(elapsed {elapsed:6.1f}s)",
            flush=True,
        )

    def on_initial_pair():
        print(
            f"[mapper] initial pair registered after {time.time() - start_ts:.1f}s",
            flush=True,
        )

    maps = pycolmap.incremental_mapping(
        database_path,
        image_dir_path,
        output_folder,
        options=mapper_options,
        initial_image_pair_callback=on_initial_pair,
        next_image_callback=on_next_image,
    )
    if not maps:
        # Fall back to the most recent on-disk snapshot if BA aborted
        # before the in-memory reconstruction could be returned.
        recovered = _load_latest_snapshot(snapshot_path)
        if recovered is None:
            raise RuntimeError(
                "incremental_mapping produced no reconstructions and no "
                f"snapshot was saved under {snapshot_path}. Check the "
                f"database at {database_path} and image overlap."
            )
        print(
            f"[mapper] recovered reconstruction from snapshot: {recovered}",
            flush=True,
        )
        reconstruction = pycolmap.Reconstruction(recovered)
    else:
        print(maps)
        reconstruction = maps[0]

    reconstruction.write(output_folder)
    reconstruction.export_PLY(os.path.join(output_folder, "sparse.ply"))

    os.makedirs(mvs_path, exist_ok=True)
    pycolmap.undistort_images(mvs_path, output_folder, image_dir_path)
    pms_options = pycolmap.PatchMatchOptions()
    pms_options.num_iterations = rc.PMS_NUM_ITERATIONS
    pms_options.window_step = rc.PMS_WINDOW_STEP
    pms_options.geom_consistency = rc.PMS_GEOM_CONSISTENCY
    pms_options.max_image_size = rc.PMS_MAX_IMAGE_SIZE
    pms_options.gpu_index = rc.PMS_GPU_INDEX
    # window_step >= 2 means each depth map only stores ~1/step^2 of pixels.
    # The default per-pixel filter (min_num_consistent=2, min_tri_angle=3°) then requires that neighbor views have a depth sample at the same subsampled location.
    pycolmap.patch_match_stereo(mvs_path, options=pms_options)

    # patch_match_stereo above runs with geom_consistency=False, so only
    # photometric depth maps exist. Tell fusion to read those instead of the
    # default geometric maps. Also drop min_num_pixels to match the sparser
    # depth maps - default 5 supporting pixels per fused point is unrealistic
    # when window_step=3 already removed 8/9 of them.
    fusion_options = pycolmap.StereoFusionOptions()
    fusion_options.min_num_pixels = rc.FUSION_MIN_NUM_PIXELS
    fusion_options.max_reproj_error = rc.FUSION_MAX_REPROJ_ERROR
    fusion_options.max_normal_error = rc.FUSION_MAX_NORMAL_ERROR
    pycolmap.stereo_fusion(
        os.path.join(mvs_path, "dense.ply"),
        mvs_path,
        input_type=rc.FUSION_INPUT_TYPE,
        options=fusion_options,
    )


def _load_latest_snapshot(snapshot_path):
    if not os.path.isdir(snapshot_path):
        return None
    candidates = [
        os.path.join(snapshot_path, name)
        for name in os.listdir(snapshot_path)
        if os.path.isdir(os.path.join(snapshot_path, name))
    ]
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)

# Gets y-midpoint (index 0) and total height (index 1)
def get_vertical_details(reconstruction):
    coords = np.array([point3D.xyz for point3D in reconstruction.points3D.values()])
    list_of_y_values = coords[:, 1]
    return [((max(list_of_y_values) + min(list_of_y_values)) / 2), abs(max(list_of_y_values) - min(list_of_y_values))]

# Gets points within a certain y-boundary from the midpoint. Precision denotes how much of the height will be factored in for using points. (Ex. 0.1 is 0.1 of the total height.) Recommend using precision that is < 0.2 and > 0.
# Uses these points to get the dimensions of the coral prop for resizing.
# Returns the larger of the two dimensions (index 0) and the lesser (index 2). Assumes that boundary used to scale is the longer of the two.
def get_reconstruction_resize_dimensions(reconstruction, precision):
    coords = np.array([point3D.xyz for point3D in reconstruction.points3D.values()])
    y_details = get_vertical_details(reconstruction)
    y_height = y_details[1] * precision
    y_mid = y_details[0] - (y_details[1] * 0.1)
    mask = (coords[:, 1] <= y_mid + y_height) & (coords[:, 1] >= y_mid - y_height)
    filtered_coords = coords[mask]
    list_of_x_values = filtered_coords[:, 0]
    list_of_z_values = filtered_coords[:, 2]
    x_total = abs(max(list_of_x_values) - min(list_of_x_values))
    z_total = abs(max(list_of_z_values) - min(list_of_z_values))
    return (max(x_total, z_total), min(x_total, z_total))

def resize_dimensions(reconstruction, given_dimension, reconstruction_dimensions):
    scale = given_dimension / reconstruction_dimensions[0]
    transform = pycolmap.SimilarityTransform3(
        scale,
        np.array([1, 0, 0, 0], dtype=np.float64),
        np.array([0, 0, 0], dtype=np.float64)
    )
    reconstruction.transform(transform)

def create_mesh():
    # Turns the dense point cloud produced by stereo_fusion into a triangle mesh on disk, then launches the viewer batch script to display it.
    print("Mesh Made")

    # Directory holding the MVS outputs. dense.ply is the fused point cloud written at the end of create_3D_reconstruction; dense.obj will be the triangulated mesh we write next to it.
    wdir = Path(rc.OUTPUT_DIR_PATH + '\mvs')

    # Load the fused dense point cloud (XYZ + normals) from PLY into a MeshLib PointCloud object.
    pc = mm.loadPoints(wdir / "dense.ply")

    # Surface-reconstruct the point cloud into a triangle mesh. MeshLib uses the point normals to orient triangles; output is a watertight-ish mesh suitable for visualization/measurement.
    nefertiti_mesh = mm.triangulatePointCloud(pc)

    # Persist the mesh as Wavefront OBJ alongside the source point cloud.
    mm.saveMesh(nefertiti_mesh, wdir / "dense.obj")

    # Hand off to the external viewer script (opens dense.obj in whichever viewer modelOpen.bat is configured to launch).
    bat = Path(__file__).parent / "modelOpen.bat"
    subprocess.run([str(bat)], shell=True)


# Creates the hotkey
keyboard.add_hotkey(rc.START_KEYBIND, start_hotkey)

wait = keyboard.wait('esc')  # Wait for the 'esc' key to be pressed
sys.exit(0)  # Exit the script