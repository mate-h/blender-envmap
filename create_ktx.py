#!/usr/bin/env python3

import os
import sys
import subprocess
import glob

# Define mip levels (0-9)
MIP_LEVELS = list(range(9))
VK_FORMAT = "R16G16B16A16_SFLOAT"

def ensure_directory(path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def create_specular_ktx(input_dir, output_name, output_dir="assets", progress=None, task_id=None):
    """Create a specular KTX2 file from the cubemap faces.
    
    Args:
        input_dir: Directory containing the mip level directories
        output_name: Base name for output file
        output_dir: Directory to save the KTX file
        progress: Optional progress bar instance
        task_id: Optional task ID for the progress bar
        
    Returns:
        Tuple of (success, file_path, file_size_mb)
    """
    ensure_directory(output_dir)
    
    # Set output file path
    ktx_path = os.path.join(output_dir, f"{output_name}_specular.ktx2")
    
    # Create KTX command
    ktx_cmd = [
        "ktx", "create",
        "--format", VK_FORMAT,
        "--assign-tf", "linear",
        "--cubemap",
        "--zstd", "3",
        # Maximum level count is 10 for 512x512 base image (512, 256, 128, 64, 32, 16, 8, 4, 2, 1)
        "--levels", "9"
    ]
    
    # Collect all input files first to check existence
    input_files = []
    missing_files = []
    
    # Update progress if provided
    if progress and task_id is not None:
        progress.update(task_id, description="[cyan]Checking specular files", advance=0.2)
        progress.refresh()
    
    # Add all the input files in mip level order
    for mip_level in MIP_LEVELS:
        mip_dir = os.path.join(input_dir, f"mip{mip_level}")
        if not os.path.exists(mip_dir):
            # Skip silently
            continue
            
        # Add the 6 faces in correct order
        for i in range(1, 7):
            face_file = os.path.join(mip_dir, f"{i:04d}.exr")
            if not os.path.exists(face_file):
                missing_files.append(face_file)
            else:
                input_files.append(face_file)
    
    # Check if any files are missing
    if missing_files:
        return False, None, 0
    
    # Add all files to command
    ktx_cmd.extend(input_files)
    
    # Add output file
    ktx_cmd.append(ktx_path)
    
    # Update progress if provided
    if progress and task_id is not None:
        progress.update(task_id, description="[cyan]Creating specular KTX2", advance=0.3)
        progress.refresh()
    
    try:
        # Run the command and capture output
        result = subprocess.run(ktx_cmd, capture_output=True, text=True)
            
        if result.returncode != 0:
            return False, None, 0
        
        # Get file size
        file_size_mb = os.path.getsize(ktx_path) / (1024 * 1024)
        
        # Update progress if provided
        if progress and task_id is not None:
            progress.update(task_id, advance=0.3)
            progress.refresh()
        
        return True, ktx_path, file_size_mb
    except Exception:
        return False, None, 0

def create_diffuse_ktx(input_dir, output_name, output_dir="assets", progress=None, task_id=None):
    """Create a diffuse KTX2 file from the cubemap faces.
    
    Args:
        input_dir: Directory containing the diffuse directory
        output_name: Base name for output file
        output_dir: Directory to save the KTX file
        progress: Optional progress bar instance
        task_id: Optional task ID for the progress bar
        
    Returns:
        Tuple of (success, file_path, file_size_mb)
    """
    ensure_directory(output_dir)
    
    # Use the dedicated diffuse directory
    diffuse_dir = os.path.join(input_dir, "diffuse")
    if not os.path.exists(diffuse_dir):
        return False, None, 0
    
    # Set output file path
    ktx_path = os.path.join(output_dir, f"{output_name}_diffuse.ktx2")
    
    # Create KTX command
    ktx_cmd = [
        "ktx", "create",
        "--format", VK_FORMAT,
        "--assign-tf", "linear",
        "--levels", "1",
        "--cubemap",
        "--zstd", "3"
    ]
    
    # Collect input files and check for existence
    input_files = []
    missing_files = []
    
    # Update progress if provided
    if progress and task_id is not None:
        progress.update(task_id, description="[cyan]Checking diffuse files", advance=0.1)
        progress.refresh()
    
    # Add the 6 faces in correct order
    for i in range(1, 7):
        face_file = os.path.join(diffuse_dir, f"{i:04d}.exr")
        if not os.path.exists(face_file):
            missing_files.append(face_file)
        else:
            input_files.append(face_file)
    
    # Check if any files are missing
    if missing_files:
        return False, None, 0
    
    # Add all files to command
    ktx_cmd.extend(input_files)
    
    # Add output file
    ktx_cmd.append(ktx_path)
    
    # Update progress if provided
    if progress and task_id is not None:
        progress.update(task_id, description="[cyan]Creating diffuse KTX2", advance=0.1)
        progress.refresh()
    
    try:
        # Run the command and capture output
        result = subprocess.run(ktx_cmd, capture_output=True, text=True)
            
        if result.returncode != 0:
            return False, None, 0
        
        # Get file size
        file_size_mb = os.path.getsize(ktx_path) / (1024 * 1024)
        
        # Update progress if provided
        if progress and task_id is not None:
            progress.update(task_id, advance=0.1)
            progress.refresh()
        
        return True, ktx_path, file_size_mb
    except Exception:
        return False, None, 0

def create_ktx_files(input_dir="output/cropped", output_name="cubemap", output_dir="assets", progress=None, task_id=None):
    """Create both specular and diffuse KTX2 files.
    
    Args:
        input_dir: Directory containing the mip level and diffuse directories
        output_name: Base name for output files
        output_dir: Directory to save the KTX files
        progress: Optional progress bar instance
        task_id: Optional task ID for the progress bar
        
    Returns:
        Tuple of (success, dict_with_file_info)
    """
    # Update initial progress
    if progress and task_id is not None:
        progress.update(task_id, total=1.0, completed=0.0, description="[cyan]Creating KTX files")
        progress.refresh()
    
    # Create specular KTX
    spec_success, spec_path, spec_size = create_specular_ktx(input_dir, output_name, output_dir, progress, task_id)
    if not spec_success:
        return False, {}
    
    # Create diffuse KTX
    diff_success, diff_path, diff_size = create_diffuse_ktx(input_dir, output_name, output_dir, progress, task_id)
    if not diff_success:
        return False, {}
    
    # Update final progress
    if progress and task_id is not None:
        progress.update(task_id, completed=1.0, description="[cyan]KTX files created")
        progress.refresh()
    
    # Return success and file info
    return True, {
        "specular": {"path": spec_path, "size_mb": spec_size},
        "diffuse": {"path": diff_path, "size_mb": diff_size}
    }

# Keep a simple main function for command-line use
if __name__ == "__main__":
    # Parse command line arguments manually
    input_dir = "output/cropped"
    output_name = "cubemap"
    output_dir = "assets"
    
    # Simple argument parsing
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--input" and i+1 < len(args):
            input_dir = args[i+1]
        elif arg == "--output" and i+1 < len(args):
            output_dir = args[i+1]
        elif arg == "--name" and i+1 < len(args):
            output_name = args[i+1]
    
    # Run the main function
    success, file_info = create_ktx_files(input_dir, output_name, output_dir)
    
    if not success:
        sys.exit(1)
    
    # Successfully exit
    sys.exit(0) 