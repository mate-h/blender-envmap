import bpy
import sys
import os
import shutil
import subprocess

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
    roughness_values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

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

    for roughness in roughness_values:
        print(f"\nProcessing roughness: {roughness}")
        
        base_size = 512
        mip_level = int(roughness * 10)
        resolution = base_size // (2 ** mip_level)
        
        # Set render resolution
        bpy.context.scene.render.resolution_x = resolution
        bpy.context.scene.render.resolution_y = resolution
        print(f"Setting render resolution to {resolution}x{resolution}")
        
        # Set output path for this roughness level
        roughness_dir = os.path.join(output_dir, f"roughness_{roughness}")
        os.makedirs(roughness_dir, exist_ok=True)
        bpy.context.scene.render.filepath = os.path.join(roughness_dir, "")
        print(f"Setting output path to: {roughness_dir}")
        
        # Look in the World node tree instead of materials
        # if bpy.data.worlds and bpy.data.worlds[0].use_nodes:
        #     world = bpy.data.worlds[0]
        #     print(f"Checking World: {world.name}")
            
        #     for node in world.node_tree.nodes:
        #         print(f"Node: {node.name}")
        #         print(f"Type: {node.type}")
                
        #         if node.type == 'TEX_ENVIRONMENT':
        #             node.image.filepath = env_map_path
        #             print(f"Updated environment map to: {env_map_path}")
        #             break

        set_material(roughness, 1)
        
        # Render the current roughness level
        bpy.ops.render.render(animation=True)

        # if resolution is less than 4, scale the output images with the oiiotool
        files = os.listdir(roughness_dir)
        for file in files:
            if file.endswith(".exr"):
                if resolution < 4:
                    oiiotool_cmd = [
                        "oiiotool",
                        "-resize", f"{resolution}x{resolution}",
                        os.path.join(roughness_dir, file),
                        "-o", os.path.join(roughness_dir, file)
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

    # Create KTX2 file for specular
    ktx_name = os.path.splitext(os.path.basename(env_map_path))[0]
    ktx_path = f"assets/{ktx_name}_specular.ktx2"
    
    ktx_cmd = [
        "ktx", "create",
        "--format", "R16G16B16A16_SFLOAT",
        "--assign-tf", "linear",
        "--cubemap",
        "--zstd", "3",
        "--levels", str(len(roughness_values))
    ]
    
    # Add all the input files
    for roughness in roughness_values:
        roughness_dir = os.path.join(output_dir, f"roughness_{roughness}")
        for i in range(1, 7):
            ktx_cmd.append(os.path.join(roughness_dir, f"{i:04d}.exr"))
    
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
        "--format", "R16G16B16A16_SFLOAT",
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
