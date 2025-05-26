#!/usr/bin/env python3
"""
Shared configuration and constants for the blender-envmap project.
"""

# Mip levels configuration
MIP_LEVELS = list(range(10))  # 0-9
BASE_RESOLUTION = 512

def get_mip_levels_for_ktx(skip_last_mip=True):
    """Get the mip levels to use for KTX creation.
    
    Args:
        skip_last_mip: Whether to skip mip level 9 (1x1 per face)
        
    Returns:
        List of mip levels to include
    """
    if skip_last_mip:
        return list(range(9))  # 0-8
    else:
        return MIP_LEVELS  # 0-9

def get_ktx_levels_count(skip_last_mip=True):
    """Get the number of levels for KTX creation.
    
    Args:
        skip_last_mip: Whether to skip mip level 9
        
    Returns:
        String representation of the number of levels
    """
    return str(len(get_mip_levels_for_ktx(skip_last_mip)))

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