import bpy
import sys

# Define path to the model
model_path = r"C:\Users\ROV\Documents\Photogrammetry\Output\mvs\dense.obj"

# Clear existing mesh objects in the scene (optional)
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.select_by_type(type='MESH')
bpy.ops.object.delete()

# Import the model based on file extension
if model_path.endswith('.fbx'):
    bpy.ops.import_scene.fbx(filepath=model_path)
elif model_path.endswith('.obj'):
    bpy.ops.wm.obj_import(filepath=model_path)
elif model_path.endswith('.glb') or model_path.endswith('.gltf'):
    bpy.ops.import_scene.gltf(filepath=model_path)

# Save as a new .blend file (optional)
# bpy.ops.wm.save_as_mainfile(filepath="C:\\path\\to\\new_scene.blend")
