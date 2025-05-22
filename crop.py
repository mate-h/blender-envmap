#!/usr/bin/env python3

import os
import subprocess
import glob
import asyncio
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
from concurrent.futures import ThreadPoolExecutor

# Output directory
OUTPUT_DIR = "output/cropped"

# Define mip levels (0-9)
MIP_LEVELS = list(range(10))

# Set up rich console
console = Console()

async def extract_cubemap_face(input_path, output_path, x, y, size):
    """Extract a face from the cubemap image using oiiotool."""
    try:
        # Create the oiiotool command with proper cropping
        # Using --cut instead of --crop to extract the region without black areas
        # Adjust the end coordinates to ensure exact size (end coordinate is exclusive)
        cmd = [
            "oiiotool",
            input_path,
            "--cut", f"{x},{y},{x+size-1},{y+size-1}",  # Subtract 1 from end coordinates to get exact size
            "-o", output_path
        ]
        
        # Run the command asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            console.print(f"[bold red]Error processing {input_path}: {stderr.decode()}[/bold red]")
            return False
            
        # Verify the output image dimensions (run synchronously)
        loop = asyncio.get_event_loop()
        verify_cmd = ["oiiotool", "--info", "-v", output_path]
        
        verify_process = await asyncio.create_subprocess_exec(
            *verify_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        verify_stdout, verify_stderr = await verify_process.communicate()
        info_output = verify_stdout.decode().strip()
        
        # Check if the size is correct
        if f"{size} x {size}" not in info_output:
            # console.print(f"[yellow]Warning: Output image may not be exactly {size}x{size}[/yellow]")
            
            # Try to resize to exact size if needed
            resize_cmd = [
                "oiiotool",
                output_path,
                "-o", output_path
            ]
            
            resize_process = await asyncio.create_subprocess_exec(
                *resize_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            resize_stdout, resize_stderr = await resize_process.communicate()
            if resize_process.returncode != 0:
                console.print(f"[bold red]Error resizing: {resize_stderr.decode()}[/bold red]")
        
        return True
    except Exception as e:
        console.print(f"[bold red]Exception processing {input_path}: {e}[/bold red]")
        return False

async def process_roughness_level(roughness_index, output_subdir=None, progress=None, task_id=None):
    """Process a specific mip level."""
    # Use mip level for filenames instead of roughness values
    mip_level = roughness_index
    input_file = f"output/cubemap_mip{mip_level}.hdr"
    
    # Calculate face size based on mip level
    base_size = 512
    size = base_size // (2 ** mip_level)
    
    # Define the target directory
    target_dir = OUTPUT_DIR
    if output_subdir:
        target_dir = os.path.join(OUTPUT_DIR, output_subdir)
    
    # Create target directory if it doesn't exist
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    
    # Check if input file exists
    if not os.path.exists(input_file):
        console.print(f"[bold red]Input file not found: {input_file}[/bold red]")
        return False
    
    # Get input image dimensions
    process = await asyncio.create_subprocess_exec(
        "oiiotool", "--info", "-v", input_file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    # Define face positions for extraction
    faces = [
        ("0001.exr", size*3, size),    # BACK
        ("0002.exr", size, size),      # FRONT
        ("0003.exr", size*2, 0),       # TOP
        ("0004.exr", size*2, size*2),  # BOTTOM
        ("0005.exr", size*2, size),    # RIGHT
        ("0006.exr", 0, size),         # LEFT
    ]
    
    success = True
    face_tasks = []
    
    # Create a sub-progress for faces if we have a progress bar
    face_progress = None
    face_task_id = None
    if progress:
        face_progress = progress
        face_task_id = progress.add_task(f"[cyan]Mip {mip_level} faces", total=len(faces))
    
    # Process all faces in parallel
    for idx, (output_file, x, y) in enumerate(faces):
        # Add mip level to filename if needed
        if output_subdir is None:
            final_output_file = f"mip{mip_level}_{output_file}"
        else:
            final_output_file = output_file
            
        output_path = os.path.join(target_dir, final_output_file)
        
        # Create a task for this face extraction
        face_tasks.append(extract_cubemap_face(input_file, output_path, x, y, size))
    
    # Wait for all face extractions to complete
    face_results = await asyncio.gather(*face_tasks)
    
    # Update the progress bar for this mip level's faces
    if face_progress and face_task_id is not None:
        face_progress.update(face_task_id, completed=len(faces))
    
    # Update the progress of the mip level if provided
    if progress and task_id is not None:
        progress.update(task_id, advance=1)
    
    # Check if all faces were extracted successfully
    if not all(face_results):
        success = False
    
    return success

async def process_diffuse_cubemap(progress=None, task_id=None, external_progress=False):
    """Process the diffuse cubemap into its own folder with specified face size."""
    input_file = "output/cubemap_diffuse.hdr"
    
    # Fixed size for diffuse cubemap (512x512 per face)
    size = 32
    
    # Define diffuse target directory
    diffuse_dir = os.path.join(OUTPUT_DIR, "diffuse")
    
    # Create diffuse directory if it doesn't exist
    if not os.path.exists(diffuse_dir):
        os.makedirs(diffuse_dir, exist_ok=True)
    
    # Check if input file exists
    if not os.path.exists(input_file):
        console.print(f"[bold red]Input file not found: {input_file}[/bold red]")
        return False
    
    # Create task ID for diffuse if we have a progress bar and not using external progress
    diffuse_task_id = None
    if progress and not external_progress:
        diffuse_task_id = progress.add_task("[green]Diffuse cubemap", total=6)
    elif progress and external_progress and task_id is not None:
        # Update external progress if provided
        progress.update(task_id, description="[cyan]Cropping diffuse cubemap")
    
    # Define face positions for extraction (same layout as specular maps)
    faces = [
        ("0001.exr", size*3, size),    # BACK
        ("0002.exr", size, size),      # FRONT
        ("0003.exr", size*2, 0),       # TOP
        ("0004.exr", size*2, size*2),  # BOTTOM
        ("0005.exr", size*2, size),    # RIGHT
        ("0006.exr", 0, size),         # LEFT
    ]
    
    success = True
    face_tasks = []
    
    # Process all faces in parallel
    for output_file, x, y in faces:
        output_path = os.path.join(diffuse_dir, output_file)
        face_tasks.append(extract_cubemap_face(input_file, output_path, x, y, size))
    
    # Wait for all face extractions to complete
    face_results = await asyncio.gather(*face_tasks)
    
    # Update progress bar if provided and not using external progress
    if progress and diffuse_task_id is not None and not external_progress:
        progress.update(diffuse_task_id, completed=6)
    elif progress and external_progress and task_id is not None:
        # Update external progress if provided
        progress.update(task_id, advance=1/11)  # Advance by 1/11th of total
    
    # Check if all faces were extracted successfully
    if not all(face_results):
        success = False
    
    return success

async def process_mip_levels(external_progress=None, external_task_id=None):
    """Process all mip levels in parallel.
    
    Args:
        external_progress: Optional external Progress instance
        external_task_id: Optional task ID in the external progress
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Determine if we're using external progress or creating our own
    using_external_progress = external_progress is not None and external_task_id is not None
    
    # Create a rich progress display with custom formatting if not using external progress
    progress_context = external_progress if using_external_progress else Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console
    )
    
    # Use a context manager only if we're creating our own progress bar
    if not using_external_progress:
        progress_context = progress_context.__enter__()
    
    try:
        # If using external progress, update its description
        if using_external_progress:
            external_progress.update(external_task_id, description="[cyan]Cropping mip levels")
        
        # Add a task for processing all mip levels if not using external progress
        mip_task_id = None
        if not using_external_progress:
            mip_task_id = progress_context.add_task("[magenta]Processing mip levels", total=len(MIP_LEVELS))
        
        # Create tasks for all mip levels
        tasks = []
        for i, mip_level in enumerate(MIP_LEVELS):
            mip_dir = f"mip{mip_level}"
            # Pass the progress if not using external progress
            if not using_external_progress:
                tasks.append(process_roughness_level(mip_level, mip_dir, progress_context, mip_task_id))
            else:
                # Process without nested progress bars
                tasks.append(process_roughness_level(mip_level, mip_dir))
                # Update external progress after each mip level
                if i > 0:  # Only update after first mip level to avoid jumping too fast
                    external_progress.update(external_task_id, advance=1/11)  # Advance by 1/11th of total
        
        # Process diffuse map
        if using_external_progress:
            diffuse_task = process_diffuse_cubemap(external_progress, external_task_id, True)
        else:
            diffuse_task = process_diffuse_cubemap(progress_context)
        tasks.append(diffuse_task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        # Update external progress to complete if using it
        if using_external_progress:
            external_progress.update(external_task_id, advance=1/11, description="[cyan]Cropping complete")
        
        console.print("[bold green]Cubemap extraction complete![/bold green]")
        
        # Return True if all tasks succeeded
        return all(results)
        
    finally:
        # Exit the context manager if we created our own progress bar
        if not using_external_progress:
            progress_context.__exit__(None, None, None)

if __name__ == "__main__":
    # Run the async main function without external progress
    asyncio.run(process_mip_levels()) 