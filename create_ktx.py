#!/usr/bin/env python3

import os
import sys
import subprocess
import glob
import argparse
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table

# Set up rich console
console = Console()

# Define mip levels (0-9)
MIP_LEVELS = list(range(9))
VK_FORMAT = "E5B9G9R9_UFLOAT_PACK32"
VK_FORMAT = "R16G16B16A16_SFLOAT"

def ensure_directory(path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def create_specular_ktx(input_dir, output_name, output_dir="assets", progress=None):
    """Create a specular KTX2 file from the cubemap faces."""
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
    
    # Create task for checking files if progress is provided
    check_task_id = None
    if progress:
        check_task_id = progress.add_task("[cyan]Checking specular files", total=len(MIP_LEVELS) * 6)
    
    # Add all the input files in mip level order
    for mip_level in MIP_LEVELS:
        mip_dir = os.path.join(input_dir, f"mip{mip_level}")
        if not os.path.exists(mip_dir):
            console.print(f"[yellow]Warning: Mip directory not found: {mip_dir}[/yellow]")
            if progress and check_task_id is not None:
                progress.update(check_task_id, advance=6)  # Skip 6 files
            continue
            
        # Add the 6 faces in correct order
        for i in range(1, 7):
            face_file = os.path.join(mip_dir, f"{i:04d}.exr")
            if not os.path.exists(face_file):
                missing_files.append(face_file)
                console.print(f"[bold red]Error: Face file not found: {face_file}[/bold red]")
            else:
                input_files.append(face_file)
            
            # Update progress if available
            if progress and check_task_id is not None:
                progress.update(check_task_id, advance=1)
    
    # Check if any files are missing
    if missing_files:
        console.print(Panel(f"[bold red]Missing {len(missing_files)} required files for specular KTX2[/bold red]", 
                           title="Error", border_style="red"))
        return False
    
    # Add all files to command
    ktx_cmd.extend(input_files)
    
    # Add output file
    ktx_cmd.append(ktx_path)
    
    # Create task for KTX creation if progress is provided
    ktx_task_id = None
    if progress:
        ktx_task_id = progress.add_task("[green]Creating specular KTX2", total=1)
        
    # Show command in a panel
    command_str = " ".join(ktx_cmd)
    console.print(Panel(f"[dim]{command_str}[/dim]", title="[bold blue]Creating specular KTX2 file[/bold blue]", 
                       expand=False, border_style="blue"))
    
    try:
        # Run the command and capture output
        result = subprocess.run(ktx_cmd, capture_output=True, text=True)
        
        # Update progress
        if progress and ktx_task_id is not None:
            progress.update(ktx_task_id, advance=1)
            
        if result.returncode != 0:
            console.print(f"[bold red]Error creating KTX file: {result.stderr}[/bold red]")
            return False
        
        # Show success message
        console.print(f"[bold green]Created[/bold green] {ktx_path}")
        
        # Get format info
        format_info = subprocess.run(f"ktx info {ktx_path} | grep vkFormat", 
                                   shell=True, capture_output=True, text=True)
        
        # Display format info in a table
        table = Table(show_header=False)
        table.add_row("[dim]vkFormat:[/dim]", f"[cyan]{format_info.stdout.strip().split(': ')[1]}[/cyan]")
        console.print(table)
        
        return True
    except Exception as e:
        console.print(f"[bold red]Exception during KTX creation: {e}[/bold red]")
        return False

def create_diffuse_ktx(input_dir, output_name, output_dir="assets", progress=None):
    """Create a diffuse KTX2 file from the cubemap faces."""
    ensure_directory(output_dir)
    
    # Use the dedicated diffuse directory instead of mip9
    diffuse_dir = os.path.join(input_dir, "diffuse")
    if not os.path.exists(diffuse_dir):
        console.print(f"[bold red]Error: Diffuse directory not found: {diffuse_dir}[/bold red]")
        return False
    
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
    
    # Create task for checking files if progress is provided
    check_task_id = None
    if progress:
        check_task_id = progress.add_task("[cyan]Checking diffuse files", total=6)
    
    # Add the 6 faces in correct order
    for i in range(1, 7):
        face_file = os.path.join(diffuse_dir, f"{i:04d}.exr")
        if not os.path.exists(face_file):
            missing_files.append(face_file)
            console.print(f"[bold red]Error: Diffuse face file not found: {face_file}[/bold red]")
        else:
            input_files.append(face_file)
        
        # Update progress if available
        if progress and check_task_id is not None:
            progress.update(check_task_id, advance=1)
    
    # Check if any files are missing
    if missing_files:
        console.print(Panel(f"[bold red]Missing {len(missing_files)} required files for diffuse KTX2[/bold red]", 
                           title="Error", border_style="red"))
        return False
    
    # Add all files to command
    ktx_cmd.extend(input_files)
    
    # Add output file
    ktx_cmd.append(ktx_path)
    
    # Create task for KTX creation if progress is provided
    ktx_task_id = None
    if progress:
        ktx_task_id = progress.add_task("[green]Creating diffuse KTX2", total=1)
    
    # Show command in a panel
    command_str = " ".join(ktx_cmd)
    console.print(Panel(f"[dim]{command_str}[/dim]", title="[bold blue]Creating diffuse KTX2 file[/bold blue]", 
                       expand=False, border_style="blue"))
    
    try:
        # Run the command and capture output
        result = subprocess.run(ktx_cmd, capture_output=True, text=True)
        
        # Update progress
        if progress and ktx_task_id is not None:
            progress.update(ktx_task_id, advance=1)
            
        if result.returncode != 0:
            console.print(f"[bold red]Error creating diffuse KTX file: {result.stderr}[/bold red]")
            return False
        
        # Show success message
        console.print(f"[bold green]Created[/bold green] {ktx_path}")
        
        # Get format info
        format_info = subprocess.run(f"ktx info {ktx_path} | grep vkFormat", 
                                   shell=True, capture_output=True, text=True)
        
        # Display format info in a table
        table = Table(show_header=False)
        table.add_row("[dim]vkFormat:[/dim]", f"[cyan]{format_info.stdout.strip().split(': ')[1]}[/cyan]")
        console.print(table)
        
        return True
    except Exception as e:
        console.print(f"[bold red]Exception during diffuse KTX creation: {e}[/bold red]")
        return False

def main():
    """Process command line arguments and create KTX files."""
    parser = argparse.ArgumentParser(description="Create KTX2 files from cubemap faces")
    parser.add_argument("--input", default="output/cropped", help="Input directory containing roughness subdirectories")
    parser.add_argument("--output", default="assets", help="Output directory for KTX files")
    parser.add_argument("--name", default="cubemap", help="Base name for output KTX files")
    args = parser.parse_args()
    
    # Display a fancy header
    console.print(Panel("[bold]KTX2 Environment Map Generator[/bold]", 
                       subtitle="Creating PBR cubemaps for Bevy", 
                       border_style="cyan"))
    
    # Show settings table
    settings = Table(show_header=True, header_style="bold cyan")
    settings.add_column("Setting")
    settings.add_column("Value")
    settings.add_row("Input Path", args.input)
    settings.add_row("Output Path", args.output)
    settings.add_row("Base Name", args.name)
    console.print(settings)
    
    # Create rich progress display
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        # Create specular KTX
        if not create_specular_ktx(args.input, args.name, args.output, progress):
            console.print("[bold red]Failed to create specular KTX[/bold red]")
            sys.exit(1)
        
        # Create diffuse KTX
        if not create_diffuse_ktx(args.input, args.name, args.output, progress):
            console.print("[bold red]Failed to create diffuse KTX[/bold red]")
            sys.exit(1)
    
    # Show success message
    console.print(Panel(f"[bold green]Successfully created KTX files in {args.output} directory[/bold green]", 
                       border_style="green"))

if __name__ == "__main__":
    main() 