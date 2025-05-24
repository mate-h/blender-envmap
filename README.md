# blender-envmap

A command-line tool that generates KTX2 environment maps for the Bevy game engine using Blender, EXR, and KTX tools.

## Prerequisites

1. **Blender**
   - Download from [blender.org](https://www.blender.org/download/)
   - Ensure command-line tools are enabled
   - Add to PATH (MacOS example with Fish shell):
     ```bash
     fish_add_path /Applications/Blender.app/Contents/MacOS
     ```

2. **OpenImageIO**
   ```bash
   brew install openimageio
   ```

3. **KTX CLI**
   - Download from [KTX-Software releases](https://github.com/KhronosGroup/KTX-Software/releases)
   - For MacOS: Install `KTX-Software-4.4.0-Darwin-arm64.pkg`

## Usage

Generate environment maps by running (example showing the default values):
```bash
blender-envmap --white-point 1.0 --name cubemap --output assets assets/spiaggia_di_mondello_2k.exr
```

The generated files will be saved in the output directory, using the name argument with specular and diffuse suffixes.

## Parameters

- White Point: This will determine the contribution of strong directional lights, the higher the value, the more the directional lights will contribute to the environment map. By default it's 1.0, so little to no contribution. When transferring the environment map to the game engine, we should instead place directional light components into the scene with the same intensity and direction.
- Name: The name of the environment map file.
- Output: The output directory for the environment map files.
- Blend File: The path to the Blender file to use for baking the environment map.