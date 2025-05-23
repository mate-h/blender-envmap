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
blender-envmap --clamp 1.0 --name cubemap --output assets assets/spiaggia_di_mondello_2k.exr
```

The generated files will be saved in the output directory, using the name argument with specular and diffuse suffixes.
