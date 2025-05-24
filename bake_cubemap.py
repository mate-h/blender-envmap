import bpy
import os
import sys

def setup_output_directory():
    """Create and return the output directory path."""
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def get_cube_probe():
    """Get the CubeProbe object or exit if not found."""
    cube_probe = bpy.data.objects.get("CubeProbe")
    if not cube_probe:
        print("Error: CubeProbe object not found!")
        sys.exit(1)
    return cube_probe

def set_environment_texture(texture_path):
    """Set the environment texture for the world."""
    # Make sure we have a world
    if not bpy.data.worlds:
        print("Error: No world found in the scene!")
        return False
    
    world = bpy.data.worlds[0]
    
    # Verify world uses nodes
    if not world.use_nodes:
        print("Error: World does not use nodes!")
        return False
    
    nodes = world.node_tree.nodes
    
    # Find Environment Texture node
    env_tex_node = None
    for node in nodes:
        if node.type == 'TEX_ENVIRONMENT':
            env_tex_node = node
            break
    
    if not env_tex_node:
        print("Error: Environment Texture node not found in the world node tree!")
        return False
    
    # Load and assign the texture
    try:
        # Check if the image is already loaded
        image = None
        for img in bpy.data.images:
            if img.filepath == texture_path:
                image = img
                break
        
        if not image:
            # Load the image
            image = bpy.data.images.load(texture_path)
        
        # Set the texture
        env_tex_node.image = image
        print(f"Successfully set environment texture to: {texture_path}")
        return True
        
    except Exception as e:
        print(f"Error setting environment texture: {e}")
        return False

def set_white_point(white_point_value):
    """Set the value of the white point node in the world shader."""
    # Make sure we have a world
    if not bpy.data.worlds:
        print("Error: No world found in the scene!")
        return False
    
    world = bpy.data.worlds[0]
    
    # Verify world uses nodes
    if not world.use_nodes:
        print("Error: World does not use nodes!")
        return False
    
    nodes = world.node_tree.nodes
    
    # Find white point node
    white_point_node = None
    for node in nodes:
        if node.label == "WhitePoint":
            white_point_node = node
            break
    
    if not white_point_node:
        print("Error: WhitePoint node not found in the world node tree!")
        return False
    
    # Set the value
    try:
        # Check if it's a Value node
        if white_point_node.type == 'VALUE':
            # Set the value
            white_point_node.outputs[0].default_value = white_point_value
            print(f"Successfully set white point value to: {white_point_value}")
            return True
        else:
            print(f"Error: white point node is not a Value node, it's a {white_point_node.type} node")
            return False
        
    except Exception as e:
        print(f"Error setting white point value: {e}")
        return False

def create_bake_image(name, output_dir, mip_level=0):
    """Create a new image for baking with specified mip level."""
    base_size = 512
    resolution = max(1, base_size // (2 ** mip_level))  # Ensure minimum size is 8x8
    
    # Create new image with standard 1:1 aspect ratio first
    image = bpy.data.images.new(name=name, width=resolution*4, height=resolution*3, float_buffer=True)
    image.filepath = os.path.join(output_dir, f"{name}.hdr")
    image.file_format = 'HDR'
    return image

def setup_render_settings(resolution=512):
    """Configure render and bake settings."""
    # Force CPU renderer to avoid Metal GPU crashes
    # bpy.context.scene.render.engine = 'CYCLES'
    # bpy.context.scene.cycles.device = 'CPU'
    
    # bpy.context.scene.cycles.samples = 16
    # bpy.context.scene.cycles.use_denoising = False
    
    # Set render resolution
    bpy.context.scene.render.resolution_x = resolution
    bpy.context.scene.render.resolution_y = resolution

    bpy.context.scene.render.bake.use_selected_to_active = False
    bpy.context.scene.render.bake.use_cage = False
    bpy.context.scene.render.bake.use_clear = True
    
    # Disable tonemapping during baking
    bpy.context.scene.view_settings.view_transform = 'Raw'
    bpy.context.scene.view_settings.look = 'None'
    bpy.context.scene.display_settings.display_device = 'sRGB'

def select_object(obj):
    """Select the given object and make it active."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def adjust_material_roughness(material_name, roughness_value):
    """Adjust the roughness of the specified material."""
    material = bpy.data.materials.get(material_name)
    if not material:
        print(f"Error: Material '{material_name}' not found!")
        return False
    
    if not material.use_nodes:
        print(f"Error: Material '{material_name}' does not use nodes!")
        return False
    
    # Find the Principled BSDF node
    principled_node = None
    for node in material.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled_node = node
            break
    
    if not principled_node:
        print(f"Error: No Principled BSDF node found in material '{material_name}'!")
        return False
    
    # Set the roughness value
    principled_node.inputs['Roughness'].default_value = roughness_value
    return True

def setup_image_texture_node(obj, image):
    """Set up or create an image texture node for baking."""
    if not obj.active_material:
        print(f"Error: Object {obj.name} has no active material")
        return False
    
    if not obj.active_material.use_nodes:
        obj.active_material.use_nodes = True
    
    material = obj.active_material
    nodes = material.node_tree.nodes
    
    # Clear existing Image Texture nodes to avoid conflicts
    for node in list(nodes):
        if node.type == 'TEX_IMAGE' or node.bl_idname == 'ShaderNodeTexImage':
            nodes.remove(node)
    
    # Create a new Image Texture node using proper Blender 4.x naming
    try:
        tex_node = nodes.new(type='ShaderNodeTexImage')
    except Exception as e:
        print(f"Error creating ShaderNodeTexImage: {e}")
        try:
            # Fallback to older naming
            tex_node = nodes.new(type='TEX_IMAGE')
        except Exception as e2:
            print(f"Error creating TEX_IMAGE: {e2}")
            return False
    
    tex_node.image = image
    
    # Make this the active node for baking
    nodes.active = tex_node
    return True

def bake_single_cubemap(cube_probe, image, mip_level, output_dir):
    """Bake a single cubemap with specified roughness and mip level."""
    try:
        base_size = 512
        resolution = max(8, base_size // (2 ** mip_level))
        
        # Setup render settings for this mip level (CPU only)
        setup_render_settings(resolution)
        
        # Select the cube probe
        select_object(cube_probe)
        
        # Set up the image texture node for baking
        if not setup_image_texture_node(cube_probe, image):
            print(f"Error: Failed to set up image texture node")
            return False
        
        # Bake with CPU
        try:
            bpy.ops.object.bake(type='COMBINED', use_selected_to_active=False)
            # save the image to disk
            image.file_format = 'HDR'
            image.save_render(filepath=os.path.join(output_dir, f"{image.name}.hdr"))
        except Exception as e:
            print(f"Baking failed with error: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error during baking: {e}")
        return False

def bake_cubemap():
    """Main function to bake the cubemap with multiple roughness levels."""
    try:
        output_dir = setup_output_directory()
        cube_probe = get_cube_probe()
        
        # Define roughness levels properly distributed from 0.0 to 1.0 across mip levels
        # For 10 mip levels, we need 10 roughness values
        max_mip_levels = 10
        roughness_values = [i / (max_mip_levels - 1) for i in range(max_mip_levels)]
        
        # Process each roughness level
        for i, roughness in enumerate(roughness_values):
            # The mip level directly corresponds to the index
            mip_level = i
            
            # Create new image for this roughness level - use mip level in name instead of roughness
            image_name = f"cubemap_mip{mip_level}"
            image = create_bake_image(image_name, output_dir, mip_level)
            
            # Adjust material roughness
            adjust_material_roughness("BakeMaterial", roughness)
            
            # Bake the cubemap for this roughness level
            success = False
            try:
                success = bake_single_cubemap(cube_probe, image, mip_level, output_dir)
            except Exception as e:
                print(f"Exception during baking for mip{mip_level} (roughness {roughness:.2f}): {e}")
            
            if not success:
                print(f"Baking failed for mip{mip_level} (roughness {roughness:.2f})")
                # Continue with next roughness level instead of failing completely
                # Clean up the failed image
                try:
                    bpy.data.images.remove(image)
                except:
                    pass
                continue
            
            # Clean up the image after saving
            try:
                bpy.data.images.remove(image)
            except Exception as e:
                print(f"Warning: Failed to clean up image: {e}")
        
        # Create diffuse image with fixed 32x32 per face dimensions
        diffuse_image_name = "cubemap_diffuse"
        
        # Calculate the total cubemap layout size for 32x32 faces (mip 4)
        diffuse_image = create_bake_image(diffuse_image_name, output_dir, 4)
        
        # Set material to maximum roughness
        adjust_material_roughness("BakeMaterial", 1.0)
        
        # Setup render settings specifically for 32x32 diffuse map
        setup_render_settings(32)
        
        # Bake the diffuse cubemap
        success = False
        try:
            # Select the cube probe
            select_object(cube_probe)
            
            # Set up the image texture node for baking
            if not setup_image_texture_node(cube_probe, diffuse_image):
                print(f"Error: Failed to set up image texture node for diffuse map")
            else:
                bpy.ops.object.bake(type='COMBINED', use_selected_to_active=False)
                diffuse_image.file_format = 'HDR'
                diffuse_image.save_render(filepath=os.path.join(output_dir, f"{diffuse_image_name}.hdr"))
                success = True
        except Exception as e:
            print(f"Exception during baking for diffuse cubemap: {e}")
        
        if not success:
            print(f"Baking failed for diffuse cubemap")
            # Clean up the failed image
            try:
                bpy.data.images.remove(diffuse_image)
            except:
                pass
        else:
            # Clean up the image after saving
            try:
                bpy.data.images.remove(diffuse_image)
            except Exception as e:
                print(f"Warning: Failed to clean up image: {e}")
        
        return True
        
    except Exception as e:
        print(f"Fatal error: {e}")
        return False

if __name__ == "__main__":
    try:
        # Get command line arguments passed after "--"
        argv = sys.argv
        
        # Find the index of the script
        script_index = argv.index("bake_cubemap.py")
        
        # Find the "--" separator
        try:
            separator_index = argv.index("--", script_index)
            # Get arguments after "--"
            args = argv[separator_index + 1:]
            
            # Parse texture path (first argument)
            if len(args) > 0:
                texture_path = args[0]
                print(f"Setting environment texture: {texture_path}")
                
                # Set the environment texture
                if not set_environment_texture(texture_path):
                    print("Failed to set environment texture, continuing with default")
            else:
                print("No environment texture path provided, using default")
                
            # Parse white point value (second argument)
            if len(args) > 1:
                try:
                    white_point_value = float(args[1])
                    print(f"Setting white point value: {white_point_value}")
                    
                    # Set the white point value
                    if not set_white_point(white_point_value):
                        print("Failed to set white point value, continuing with default")
                except ValueError:
                    print(f"Invalid white point value: {args[1]}, must be a number")
            
        except ValueError:
            print("No command line arguments provided, using default settings")
        
        if not bake_cubemap():
            print("Baking failed!")
            sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)