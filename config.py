#!/usr/bin/env python3
"""
Shared configuration and constants for the blender-envmap project.
"""

import subprocess
import re
import math

def detect_input_resolution(image_path):
    """Detect the resolution of an input HDR/EXR image.
    
    Args:
        image_path: Path to the input image
        
    Returns:
        Tuple of (width, height) or None if detection fails
    """
    try:
        # Use oiiotool to get image info
        result = subprocess.run(
            ["oiiotool", "--info", "-v", image_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return None
            
        # Parse the output to find resolution
        # Look for pattern like "2048 x 1024" or "1024 x  512" (with variable whitespace)
        resolution_match = re.search(r'(\d+)\s+x\s+(\d+)', result.stdout)
        if resolution_match:
            width = int(resolution_match.group(1))
            height = int(resolution_match.group(2))
            return (width, height)
            
    except Exception:
        pass
    
    return None

def calculate_cubemap_resolution_from_input(input_width, input_height):
    """Calculate the appropriate cubemap face resolution from input image dimensions.
    
    For equirectangular images, the width should be 2x the height.
    The cubemap face size is typically width/4.
    
    Args:
        input_width: Width of input image
        input_height: Height of input image
        
    Returns:
        Recommended cubemap face resolution
    """
    # For equirectangular: width = 2 * height, face_size = width / 4 = height / 2
    if input_width >= input_height * 1.8:  # Allow some tolerance
        return input_height // 2
    else:
        # If not standard equirectangular, use width/4 as fallback
        return input_width // 4

def calculate_mip_levels(base_resolution):
    """Calculate the number of mip levels for a given base resolution.
    
    Args:
        base_resolution: Base cubemap face resolution
        
    Returns:
        Number of mip levels (including mip 0)
    """
    # Calculate how many times we can divide by 2 until we reach 1x1
    return int(math.log2(base_resolution)) + 1

def get_dynamic_mip_levels(base_resolution):
    """Get the list of mip levels for a given base resolution.
    
    Args:
        base_resolution: Base cubemap face resolution
        
    Returns:
        List of mip levels (e.g., [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    """
    max_mip = calculate_mip_levels(base_resolution) - 1
    return list(range(max_mip + 1))

def get_mip_levels_for_ktx(base_resolution, skip_last_mip=True):
    """Get the mip levels to use for KTX creation.
    
    Args:
        base_resolution: Base cubemap face resolution
        skip_last_mip: Whether to skip the last mip level (1x1 per face)
        
    Returns:
        List of mip levels to include
    """
    all_mips = get_dynamic_mip_levels(base_resolution)
    if skip_last_mip and len(all_mips) > 1:
        return all_mips[:-1]  # Skip the last mip level
    else:
        return all_mips

def get_ktx_levels_count(base_resolution, skip_last_mip=True):
    """Get the number of levels for KTX creation.
    
    Args:
        base_resolution: Base cubemap face resolution
        skip_last_mip: Whether to skip the last mip level
        
    Returns:
        String representation of the number of levels
    """
    return str(len(get_mip_levels_for_ktx(base_resolution, skip_last_mip)))

def get_dynamic_cubemap_configs(base_resolution):
    """Get cubemap configurations based on the base resolution.
    
    Args:
        base_resolution: Base cubemap face resolution
        
    Returns:
        Dictionary of cubemap configurations
    """
    # Calculate appropriate diffuse resolution (typically much smaller)
    diffuse_size = min(32, base_resolution // 16)  # Cap at 32, but scale down for very small resolutions
    diffuse_size = max(8, diffuse_size)  # Minimum 8x8
    
    # Calculate appropriate mip level for diffuse (where resolution matches diffuse_size)
    diffuse_mip = int(math.log2(base_resolution // diffuse_size)) if base_resolution >= diffuse_size else 0
    
    total_mips = calculate_mip_levels(base_resolution)
    
    return {
        "diffuse": {
            "size": diffuse_size,
            "mip_level": diffuse_mip,
            "roughness": 1.0,
            "resolution": diffuse_size,
            "apply_white_point": True,
            "progress_color": "[green]",
            "progress_fraction": 1/(total_mips + 1)  # +1 for diffuse
        },
        "skybox": {
            "size": base_resolution,
            "mip_level": 0,
            "roughness": 0.0,
            "resolution": base_resolution,
            "apply_white_point": False,
            "progress_color": "[blue]",
            "progress_fraction": 1/(total_mips + 2)  # +2 for diffuse and skybox
        }
    }

# Legacy static configuration (for backward compatibility)
MIP_LEVELS = list(range(10))  # 0-9
BASE_RESOLUTION = 512

# Cubemap face layout (filename, x_multiplier, y_multiplier)
CUBEMAP_FACES = [
    ("0001.exr", 3, 1),    # BACK
    ("0002.exr", 1, 1),    # FRONT
    ("0003.exr", 2, 0),    # TOP
    ("0004.exr", 2, 2),    # BOTTOM
    ("0005.exr", 2, 1),    # RIGHT
    ("0006.exr", 0, 1),    # LEFT
]

# KTX format settings
VK_FORMAT = "R16G16B16A16_SFLOAT"

# Directory structure
OUTPUT_DIRS = {
    "base": "output",
    "cropped": "output/cropped",
    "mip_template": "output/cropped/mip{level}",
    "diffuse": "output/cropped/diffuse",
    "skybox": "output/cropped/skybox"
}

# File naming patterns
FILE_PATTERNS = {
    "mip_input": "output/cubemap_mip{level}.hdr",
    "diffuse_input": "output/cubemap_diffuse.hdr",
    "skybox_input": "output/cubemap_skybox.hdr",
    "ktx_specular": "{name}_specular.ktx2",
    "ktx_diffuse": "{name}_diffuse.ktx2",
    "ktx_skybox": "{name}_skybox.ktx2"
}

# Cubemap type configurations
CUBEMAP_CONFIGS = {
    "diffuse": {
        "size": 32,
        "mip_level": 4,
        "roughness": 1.0,
        "resolution": 32,
        "apply_white_point": True,
        "progress_color": "[green]",
        "progress_fraction": 1/11
    },
    "skybox": {
        "size": 512,
        "mip_level": 0,
        "roughness": 0.0,
        "resolution": 512,
        "apply_white_point": False,
        "progress_color": "[blue]",
        "progress_fraction": 1/12
    }
}

# KTX creation configurations
KTX_CONFIGS = {
    "specular": {
        "levels": "10",
        "progress_advance": 0.3,
        "check_description": "[cyan]Checking specular files",
        "create_description": "[cyan]Creating specular KTX2"
    },
    "diffuse": {
        "levels": "1",
        "progress_advance": 0.1,
        "check_description": "[cyan]Checking diffuse files",
        "create_description": "[cyan]Creating diffuse KTX2"
    },
    "skybox": {
        "levels": "1",
        "progress_advance": 0.1,
        "check_description": "[cyan]Checking skybox files",
        "create_description": "[cyan]Creating skybox KTX2"
    }
} 