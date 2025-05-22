#!/usr/bin/env fish

# Fish shell completions for blender-envmap

# Define the command
complete -c blender-envmap -f -d "Blender Environment Map Baker"

# Positional argument for environment map
complete -c blender-envmap -n "__fish_is_first_arg" -k -f -a "(__fish_complete_suffix .hdr; __fish_complete_suffix .exr)" -d "Environment map (HDR/EXR file)"

# Option for clampat value
complete -c blender-envmap -l clamp -r -d "Value for the clamp node in world shader" 

# Option for output directory
complete -c blender-envmap -l output -r -F -d "Output directory for KTX files" 

# Option for base name
complete -c blender-envmap -l name -r -d "Base name for output KTX files" 

# Option for blend file
complete -c blender-envmap -l blend-file -r -F -a "(__fish_complete_suffix .blend)" -d "Path to Blender file" 

# Help flag
complete -c blender-envmap -s h -l help -f -d "Show help message and exit" 