#!/bin/bash

# Create local bin directory if it doesn't exist
mkdir -p ~/.local/bin

# Create fish completions directory if it doesn't exist
mkdir -p ~/.config/fish/completions

# Get the absolute path of the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Install dependencies
echo "Checking for required Python packages..."
if ! python -c "import rich" &>/dev/null; then
    echo "Installing 'rich' package..."
    pip install rich
fi

# Remove old shell script if it exists
if [ -f "blender-envmap" ]; then
    echo "Removing old shell script..."
    rm -f "blender-envmap"
fi

# Create a wrapper script that calls the Python script with the correct working directory
cat > ~/.local/bin/blender-envmap << EOF
#!/bin/bash
# This is an auto-generated wrapper for blender-envmap.py

# Change to the script directory
cd "$SCRIPT_DIR"

# Run the Python script with all arguments
python "$SCRIPT_DIR/blender-envmap.py" "\$@"
EOF

# Make the wrapper script executable
chmod +x ~/.local/bin/blender-envmap

# Install fish completions
echo "Installing Fish completions..."
cp "$SCRIPT_DIR/blender-envmap.fish" ~/.config/fish/completions/blender-envmap.fish

echo "Installation complete!"
echo "The 'blender-envmap' command is now available in ~/.local/bin"
echo "Fish completions have been installed"
echo ""
echo "If the command is not found, make sure ~/.local/bin is in your PATH by adding"
echo "this line to your shell profile (~/.bashrc, ~/.zshrc, or ~/.config/fish/config.fish):"
echo ""
echo "export PATH=\"\$HOME/.local/bin:\$PATH\"  # For bash/zsh"
echo "or"
echo "fish_add_path \$HOME/.local/bin     # For fish"
echo "" 