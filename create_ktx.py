#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
from config import VK_FORMAT, KTX_CONFIGS, FILE_PATTERNS, get_mip_levels_for_ktx, get_ktx_levels_count

def ensure_directory(path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def create_ktx_file(ktx_type, input_dir, output_name, output_dir="assets", skip_last_mip=True, base_resolution=512, progress=None, task_id=None):
    """Create a KTX2 file from cubemap faces.
    
    Args:
        ktx_type: Type of KTX file ('specular', 'diffuse', or 'skybox')
        input_dir: Directory containing the input files
        output_name: Base name for output file
        output_dir: Directory to save the KTX file
        skip_last_mip: Whether to skip the last mip level (1x1 per face) for specular KTX
        base_resolution: Base resolution for dynamic configuration
        progress: Optional progress bar instance
        task_id: Optional task ID for the progress bar
        
    Returns:
        Tuple of (success, file_path, file_size_mb)
    """
    ensure_directory(output_dir)
    
    # Configure based on KTX type
    if ktx_type not in KTX_CONFIGS:
        raise ValueError(f"Unknown KTX type: {ktx_type}")
    
    config = KTX_CONFIGS[ktx_type]
    
    if ktx_type == "specular":
        # Use filtered mip levels for specular KTX
        mip_levels_to_use = get_mip_levels_for_ktx(base_resolution, skip_last_mip)
        source_dirs = [os.path.join(input_dir, f"mip{i}") for i in mip_levels_to_use]
        # Get dynamic levels count
        levels_count = get_ktx_levels_count(base_resolution, skip_last_mip)
    elif ktx_type == "diffuse":
        source_dirs = [os.path.join(input_dir, "diffuse")]
        levels_count = config["levels"]
    elif ktx_type == "skybox":
        source_dirs = [os.path.join(input_dir, "skybox")]
        levels_count = config["levels"]
    
    ktx_path = os.path.join(output_dir, FILE_PATTERNS[f"ktx_{ktx_type}"].format(name=output_name))
    
    # Create KTX command
    ktx_cmd = [
        "ktx", "create",
        "--format", VK_FORMAT,
        "--assign-tf", "linear",
        "--levels", levels_count,
        "--cubemap",
        "--zstd", "3"
    ]
    
    # Collect input files and check for existence
    input_files = []
    missing_files = []
    
    # Update progress if provided
    if progress and task_id is not None:
        progress.update(task_id, description=f"[cyan]Checking {ktx_type} files", advance=config["progress_advance"]/3)
        progress.refresh()
    
    # Add files from source directories
    for source_dir in source_dirs:
        if not os.path.exists(source_dir):
            if ktx_type == "specular":
                continue  # Skip missing mip levels silently
            else:
                return False, None, 0  # Fail for missing diffuse/skybox dirs
        
        # Add the 6 faces in correct order
        for i in range(1, 7):
            face_file = os.path.join(source_dir, f"{i:04d}.exr")
            if not os.path.exists(face_file):
                missing_files.append(face_file)
            else:
                input_files.append(face_file)
    
    # Check if any files are missing
    if missing_files:
        return False, None, 0
    
    # Add all files to command
    ktx_cmd.extend(input_files)
    ktx_cmd.append(ktx_path)
    
    # Update progress if provided
    if progress and task_id is not None:
        progress.update(task_id, description=f"[cyan]Creating {ktx_type} KTX2", advance=config["progress_advance"]*2/3)
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
            progress.update(task_id, advance=config["progress_advance"]/3)
            progress.refresh()
        
        return True, ktx_path, file_size_mb
    except Exception:
        return False, None, 0

def create_specular_ktx(input_dir, output_name, output_dir="assets", skip_last_mip=True, base_resolution=512, progress=None, task_id=None):
    """Create a specular KTX2 file from the cubemap faces."""
    return create_ktx_file("specular", input_dir, output_name, output_dir, skip_last_mip, base_resolution, progress, task_id)

def create_diffuse_ktx(input_dir, output_name, output_dir="assets", skip_last_mip=True, base_resolution=512, progress=None, task_id=None):
    """Create a diffuse KTX2 file from the cubemap faces."""
    return create_ktx_file("diffuse", input_dir, output_name, output_dir, skip_last_mip, base_resolution, progress, task_id)

def create_skybox_ktx(input_dir, output_name, output_dir="assets", skip_last_mip=True, base_resolution=512, progress=None, task_id=None):
    """Create a skybox KTX2 file from the skybox directory."""
    return create_ktx_file("skybox", input_dir, output_name, output_dir, skip_last_mip, base_resolution, progress, task_id)

def create_ktx_files(input_dir="output/cropped", output_name="cubemap", output_dir="assets", create_skybox=False, skip_last_mip=True, base_resolution=512, progress=None, task_id=None):
    """Create specular and diffuse KTX2 files, and optionally a skybox KTX2 file.
    
    Args:
        input_dir: Directory containing the mip level and diffuse directories
        output_name: Base name for output files
        output_dir: Directory to save the KTX files
        create_skybox: Whether to create a skybox KTX file from mip0
        skip_last_mip: Whether to skip the last mip level (1x1 per face) for specular KTX
        base_resolution: Base resolution for dynamic configuration
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
    spec_success, spec_path, spec_size = create_specular_ktx(input_dir, output_name, output_dir, skip_last_mip, base_resolution, progress, task_id)
    if not spec_success:
        return False, {}
    
    # Create diffuse KTX
    diff_success, diff_path, diff_size = create_diffuse_ktx(input_dir, output_name, output_dir, skip_last_mip, base_resolution, progress, task_id)
    if not diff_success:
        return False, {}
    
    # Prepare return data
    file_info = {
        "specular": {"path": spec_path, "size_mb": spec_size},
        "diffuse": {"path": diff_path, "size_mb": diff_size}
    }
    
    # Create skybox KTX if requested
    if create_skybox:
        skybox_success, skybox_path, skybox_size = create_skybox_ktx(input_dir, output_name, output_dir, skip_last_mip, base_resolution, progress, task_id)
        if not skybox_success:
            return False, {}
        file_info["skybox"] = {"path": skybox_path, "size_mb": skybox_size}
    
    # Update final progress
    if progress and task_id is not None:
        progress.update(task_id, completed=1.0, description="[cyan]KTX files created")
        progress.refresh()
    
    # Return success and file info
    return True, file_info

# Keep a simple main function for command-line use
if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(
        prog="python create_ktx.py",
        description="Create KTX2 files from cubemap faces"
    )
    
    # Add arguments
    parser.add_argument("--input", default="output/cropped", 
                       help="Input directory containing mip level and diffuse directories (default: output/cropped)")
    parser.add_argument("--output", default="assets", 
                       help="Output directory for KTX files (default: assets)")
    parser.add_argument("--name", default="cubemap", 
                       help="Base name for output KTX files (default: cubemap)")
    parser.add_argument("--skybox", action="store_true", 
                       help="Create a skybox KTX file from mip0")
    
    # Mip level 9 control (mutually exclusive)
    last_mip_group = parser.add_mutually_exclusive_group()
    last_mip_group.add_argument("--skip-last-mip", action="store_true", default=True,
                           help="Skip last mip level (1x1 per face) in specular KTX (default)")
    last_mip_group.add_argument("--include-last-mip", action="store_true", 
                           help="Include last mip level (1x1 per face) in specular KTX")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Determine skip_last_mip setting
    skip_last_mip = not args.include_last_mip  # Skip by default unless --include-last-mip is specified
    
    # Run the main function
    success, file_info = create_ktx_files(args.input, args.name, args.output, args.skybox, skip_last_mip)
    
    if not success:
        print("Error: Failed to create KTX files")
        sys.exit(1)
    
    # Print success message
    print("Successfully created KTX files:")
    for file_type, info in file_info.items():
        file_name = os.path.basename(info["path"])
        size_mb = info["size_mb"]
        print(f"  {file_name}: {size_mb:.2f} MB")
    
    # Successfully exit
    sys.exit(0) 