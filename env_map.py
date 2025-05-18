import bpy
import sys
import os
import shutil
import subprocess
import glob

# Get arguments passed after "--" on the command line
argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []

if len(argv) >= 1:
    env_map_path = argv[0]
    print(f"Setting environment map to: {env_map_path}")
    
    # Create output directory
    output_dir = os.path.join(os.getcwd(), "output")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    # Process each roughness level
    max_mip_levels = 10
    roughness_values = [i / (max_mip_levels - 1) for i in range(max_mip_levels)]

    # Find RadianceProbe object and set its material roughness
    def set_material(roughness, metallic):
        radiance_probe = bpy.data.objects.get("RadianceProbe")
        if radiance_probe:
            if roughness == 0:
                radiance_probe.hide_render = True
                print("Hiding RadianceProbe as roughness is 0")
            else:
                radiance_probe.hide_render = False
                if radiance_probe.active_material:
                    material = radiance_probe.active_material
                    if material.use_nodes:
                        for node in material.node_tree.nodes:
                            if node.type == 'BSDF_PRINCIPLED':
                                node.inputs['Roughness'].default_value = roughness
                                node.inputs['Metallic'].default_value = metallic
                                print(f"Set RadianceProbe material roughness to {roughness}")
                                break

    # Convert HDR files to EXR in a directory
    def convert_hdr_to_exr(directory):
        hdr_files = glob.glob(os.path.join(directory, "*.hdr"))
        for hdr_file in hdr_files:
            exr_file = os.path.splitext(hdr_file)[0] + ".exr"
            print(f"Converting {hdr_file} to {exr_file}")
            subprocess.run(["oiiotool", hdr_file, "-o", exr_file])

    for i, roughness in enumerate(roughness_values):
        print(f"\nProcessing roughness: {roughness}")
        
        base_size = 512
        mip_level = i  # Using index as mip level
        resolution = base_size // (2 ** mip_level)
        
        # Set render resolution
        bpy.context.scene.render.resolution_x = resolution
        bpy.context.scene.render.resolution_y = resolution
        print(f"Setting render resolution to {resolution}x{resolution}")
        
        # Set output path for this mip level
        mip_dir = os.path.join(output_dir, f"mip{mip_level}")
        os.makedirs(mip_dir, exist_ok=True)
        bpy.context.scene.render.filepath = os.path.join(mip_dir, "")
        print(f"Setting output path to: {mip_dir}")

        set_material(roughness, 1)
        
        # Render the current roughness level
        bpy.ops.render.render(animation=True)

        # if resolution is less than 4, scale the output images with the oiiotool
        files = os.listdir(mip_dir)
        for file in files:
            if file.endswith(".hdr"):
                if resolution < 4:
                    oiiotool_cmd = [
                        "oiiotool",
                        "-resize", f"{resolution}x{resolution}",
                        os.path.join(mip_dir, file),
                        "-o", os.path.join(mip_dir, file)
                    ]
                    subprocess.run(oiiotool_cmd)
                    print(f"Scaled {file} to {resolution}x{resolution}")

    # set to 32x32
    bpy.context.scene.render.resolution_x = 32
    bpy.context.scene.render.resolution_y = 32

    # set roughness to 1
    set_material(1, 0)

    # Set output path for diffuse
    diffuse_dir = os.path.join(output_dir, "diffuse")
    os.makedirs(diffuse_dir, exist_ok=True)
    bpy.context.scene.render.filepath = os.path.join(diffuse_dir, "")
    print(f"Setting output path to: {diffuse_dir}")

    # Render the current roughness level
    bpy.ops.render.render(animation=True)


    # Convert all HDR files to EXR
    print("\nConverting HDR files to EXR format...")
    for i in range(len(roughness_values)):
        mip_dir = os.path.join(output_dir, f"mip{i}")
        convert_hdr_to_exr(mip_dir)
    
    # Convert diffuse HDR files to EXR
    convert_hdr_to_exr(diffuse_dir)
    
    print("All HDR files converted to EXR format.")

    # Create KTX2 file for specular
    ktx_name = os.path.splitext(os.path.basename(env_map_path))[0]
    ktx_path = f"assets/{ktx_name}_specular.ktx2"
    
    ktx_cmd = [
        "ktx", "create",
        "--format", "E5B9G9R9_UFLOAT_PACK32",
        "--assign-tf", "linear",
        "--cubemap",
        "--zstd", "3",
        "--levels", str(len(roughness_values))
    ]
    
    # Add all the input files
    for i in range(len(roughness_values)):
        mip_dir = os.path.join(output_dir, f"mip{i}")
        for j in range(1, 7):
            ktx_cmd.append(os.path.join(mip_dir, f"{j:04d}.exr"))
    
    # Add output file
    ktx_cmd.append(ktx_path)
    
    print(" ".join(ktx_cmd))
    
    # Execute ktx create command
    subprocess.run(ktx_cmd)
    
    print(f"\nCreated {ktx_path}")
    # Use shell=True to handle the pipe operation
    subprocess.run(f"ktx info {ktx_path} | grep vkFormat", shell=True)

    # Create KTX2 file for diffuse
    ktx_name = os.path.splitext(os.path.basename(env_map_path))[0]
    ktx_path = f"assets/{ktx_name}_diffuse.ktx2"

    ktx_cmd = [
        "ktx", "create",
        "--format", "E5B9G9R9_UFLOAT_PACK32",
        "--assign-tf", "linear",
        "--levels", "1",
        "--cubemap",
        "--zstd", "3"
    ]
    
    # Add all the input files
    diffuse_dir = os.path.join(output_dir, "diffuse")
    for i in range(1, 7):
        ktx_cmd.append(os.path.join(diffuse_dir, f"{i:04d}.exr"))
    
    # Add output file
    ktx_cmd.append(ktx_path)
    
    print(" ".join(ktx_cmd))
    
    # Execute ktx create command
    subprocess.run(ktx_cmd)

    print(f"\nCreated {ktx_path}")
    # Use shell=True to handle the pipe operation
    subprocess.run(f"ktx info {ktx_path} | grep vkFormat", shell=True)
    