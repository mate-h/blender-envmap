blender -b eq2cube.blend --python bake_cubemap.py
python crop.py
python create_ktx.py