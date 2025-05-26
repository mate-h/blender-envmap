#!/usr/bin/env python

import argparse
import os
import subprocess
import sys
import asyncio
import re
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from crop import process_mip_levels
from create_ktx import create_ktx_files

# Set up rich console
console = Console()

def ensure_directory(path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def run_command(cmd, description, progress=None, task_id=None, parse_mip=False, skybox_enabled=False):
    """Run a shell command and display output.
    
    If parse_mip is True, parse the output for mip level updates and update progress.
    """
    console.print(f"[bold blue]Running:[/bold blue] {description}")
    console.print(f"[dim]{' '.join(cmd)}[/dim]")
    
    try:
        # If we need to parse mip levels, stream the output
        if parse_mip and progress and task_id is not None:
            # Start the process with pipe for stdout and stderr
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Initialize variables to track progress
            mip_pattern = re.compile(r'Loading cubemap_mip(\d+)')
            diffuse_pattern = re.compile(r'Loading cubemap_diffuse')
            skybox_pattern = re.compile(r'Loading cubemap_skybox')
            current_mip = -1
            
            # Set the total number of steps (mip0-9 + diffuse + skybox if enabled = 11 or 12)
            total_steps = 12 if skybox_enabled else 11
            progress.update(task_id, total=total_steps)
            progress.refresh()
            
            # Process output line by line
            for line in iter(process.stdout.readline, ''):
                # Strip the line
                line = line.strip()
                
                # Print all Blender output to stdout
                print(line)
                
                # Check for mip level updates
                mip_match = mip_pattern.search(line)
                if mip_match:
                    mip_level = int(mip_match.group(1))
                    if mip_level > current_mip:
                        current_mip = mip_level
                        progress.update(task_id, completed=current_mip + 1, description=f"[cyan]Baking cubemap... (mip {current_mip})")
                        progress.refresh()
                
                # Check for diffuse map
                if diffuse_pattern.search(line):
                    progress.update(task_id, completed=11, description="[cyan]Baking cubemap... (diffuse)")
                    progress.refresh()
                
                # Check for skybox
                if skybox_pattern.search(line):
                    progress.update(task_id, completed=12, description="[cyan]Baking cubemap... (skybox)")
                    progress.refresh()
            
            # Wait for the process to complete
            process.wait()
            return process.returncode == 0
        else:
            # Run without capturing output to allow it to go to stdout
            result = subprocess.run(cmd)
            if result.returncode != 0:
                console.print(f"[bold red]Error:[/bold red] Command failed with return code {result.returncode}")
                return False
            return True
    except Exception as e:
        console.print(f"[bold red]Exception:[/bold red] {e}")
        return False

def main():
    """Main function to process command line arguments and run the environment map baking."""
    parser = argparse.ArgumentParser(
        prog="blender-envmap",
        description="Blender Environment Map Baker - Create PBR cubemaps from equirectangular HDR images"
    )
    
    # Required argument
    parser.add_argument("environment_map", help="Path to the environment map HDR file")
    
    # Optional arguments
    parser.add_argument("--white-point", type=float, help="Value for the white point node in the world shader")
    parser.add_argument("--output", default="assets", help="Output directory for KTX files")
    parser.add_argument("--name", help="Base name for output KTX files")
    parser.add_argument("--blend-file", default="eq2cube.blend", help="Path to Blender file")
    
    # Tonemap arguments (mutually exclusive)
    tonemap_group = parser.add_mutually_exclusive_group()
    tonemap_group.add_argument("--tonemap", action="store_true", default=True, help="Enable tonemapping (default)")
    tonemap_group.add_argument("--no-tonemap", action="store_true", help="Disable tonemapping")
    
    # Skybox arguments (mutually exclusive)
    skybox_group = parser.add_mutually_exclusive_group()
    skybox_group.add_argument("--skybox", action="store_true", default=True, help="Create a skybox KTX file (default)")
    skybox_group.add_argument("--no-skybox", action="store_true", help="Disable skybox creation")
    
    # Mip level 9 control (mutually exclusive)
    last_mip_group = parser.add_mutually_exclusive_group()
    last_mip_group.add_argument("--skip-last-mip", action="store_true", default=True, 
                           help="Skip last mip level (1x1 per face) in specular KTX (default)")
    last_mip_group.add_argument("--include-last-mip", action="store_true", 
                           help="Include last mip level (1x1 per face) in specular KTX")
    
    args = parser.parse_args()
    
    # Handle tonemap logic
    should_tonemap = args.tonemap and not args.no_tonemap
    
    # Handle skybox logic
    should_create_skybox = args.skybox and not args.no_skybox
    
    # Handle mip9 logic
    should_skip_last_mip = not args.include_last_mip  # Skip by default unless --include-last-mip is specified
    
    # If name is not provided, use the input file name without path or extension
    if args.name is None:
        base_name = os.path.basename(args.environment_map)
        args.name = os.path.splitext(base_name)[0]
    
    # Display a fancy header
    console.print(Panel("[bold]Blender Environment Map Baker[/bold]", 
                       subtitle="Converting HDR to PBR Cubemaps", 
                       border_style="cyan"))
    
    # Show settings table
    settings = Table(show_header=True, header_style="bold cyan")
    settings.add_column("Setting")
    settings.add_column("Value")
    settings.add_row("Environment Map", args.environment_map)
    settings.add_row("Output Directory", args.output)
    settings.add_row("Base Name", args.name)
    settings.add_row("Blend File", args.blend_file)
    settings.add_row("Tonemapping", "Enabled" if should_tonemap else "Disabled")
    settings.add_row("Skybox", "Enabled" if should_create_skybox else "Disabled")
    settings.add_row("Last Mip Level", "Skipped" if should_skip_last_mip else "Included")
    
    if args.white_point is not None:
        settings.add_row("White Point Value", str(args.white_point))
    
    console.print(settings)
    
    # Ensure the environment map exists
    if not os.path.exists(args.environment_map):
        console.print(f"[bold red]Error:[/bold red] Environment map not found: {args.environment_map}")
        return 1
    
    # Ensure the output directory exists
    ensure_directory(args.output)
    
    # Create output directories
    ensure_directory("output")
    ensure_directory("output/cropped")
    ensure_directory(args.output)
    
    # Run with progress bar
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        refresh_per_second=10,  # Lower refresh rate to avoid flicker
        auto_refresh=False      # Manual refresh for better control
    ) as progress:
        # Step 1: Bake cubemap in Blender
        task1 = progress.add_task("[cyan]Baking cubemap...", total=11)
        
        # Build the Blender command
        blender_cmd = ["blender", "-b", args.blend_file, "--python", "bake_cubemap.py", "--"]
        blender_cmd.append(args.environment_map)
        
        if args.white_point is not None:
            blender_cmd.append(str(args.white_point))
        else:
            blender_cmd.append("None")  # Placeholder for white point
        
        # Add tonemap setting
        blender_cmd.append("1" if should_tonemap else "0")
        
        # Add skybox setting
        blender_cmd.append("1" if should_create_skybox else "0")
        
        # Run blender command with progress tracking
        if not run_command(blender_cmd, "Baking cubemap", progress, task1, parse_mip=True, skybox_enabled=should_create_skybox):
            return 1
        
        # Force refresh to update the display
        progress.refresh()
        
        # Remove the completed task to prevent it from being displayed again
        progress.stop_task(task1)
        progress.refresh()
        
        # Step 2: Crop the cubemap faces (passing the progress bar to avoid nested progress bars)
        task2 = progress.add_task("[cyan]Cropping cubemap faces...", total=1)
        progress.refresh()
        
        # Direct call to process_mip_levels with our progress bar
        try:
            # Pass the white_point value to process_mip_levels
            result = asyncio.run(process_mip_levels(progress, task2, 
                                                    white_point=args.white_point))
            if not result:
                console.print("[bold red]Error in cubemap cropping process[/bold red]")
                return 1
            
            # Remove completed task
            progress.stop_task(task2)
            progress.refresh()
        except Exception as e:
            console.print(f"[bold red]Error cropping cubemap faces: {e}[/bold red]")
            return 1
        
        # Step 3: Create KTX files
        task3 = progress.add_task("[cyan]Creating KTX files...", total=1)
        progress.refresh()
        
        # Direct call to create_ktx_files instead of subprocess
        try:
            success, file_info = create_ktx_files(
                input_dir="output/cropped", 
                output_name=args.name, 
                output_dir=args.output,
                create_skybox=should_create_skybox,
                skip_last_mip=should_skip_last_mip,
                progress=progress,
                task_id=task3
            )
            
            if not success:
                console.print("[bold red]Error creating KTX files[/bold red]")
                return 1
        except Exception as e:
            console.print(f"[bold red]Error creating KTX files: {e}[/bold red]")
            return 1
        
        # Show success message
        console.print(Panel(f"[bold green]Successfully created environment map in {args.output} directory[/bold green]", 
                           border_style="green"))
        
        # Display the output files
        file_table = Table(show_header=True, header_style="bold green")
        file_table.add_column("Output Files")
        file_table.add_column("Size")
        
        for file_type, info in file_info.items():
            file_name = os.path.basename(info["path"])
            size_mb = info["size_mb"]
            file_table.add_row(file_name, f"{size_mb:.2f} MB")
        
        console.print(file_table)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 