# MTerrain Tools
A blender addon for exporting assets and scenes for use with the MTerrain addon for Godot. This is still super experimental, and I haven't had time to write proper documentation, so I apologise if this guide isn't clear. 

# Install
Download the zip from this github repo. 
Open blender preferences/addons. 
Add the zip as an addon and activate it.

# Usage
#### Simple mode: 
Create mesh objects. Rename them using the mterrain naming convetion. Click export under the N-panel / tool / mterrain.

e.g. 1 asset with 3 lods: Chair_lod_0, Chair_lod_1, Chair_lod_2.

When you import into godot's mterrain asset library it will be treated as a single object


#### Advanced Mode:
You can create multiple LOD meshes and multiple "material sets" inside one blender "object". You can link multiple "objects" into variation groups for easy swapping.

To do this, add a mesh object in blender and then convert to LOD object:
![[image.png]]

Now that it is an LOD object, press the + under "Mesh Lods". This will duplicate the mesh, and assign it to the next LOD.

If you click the eyedropper under "import lod from object", it will allow you to click on a mesh in the 3d vieport to replace the currently active lod with that mesh.

If you click the + under surface names, you can add another "surface" to this mesh. 

If you click the + under "Material Sets" you can add another material set. When you activate a material set, each surface (aka material slot) gets populated with the corresponding material from the material set. This allows you to quicky swap between a group of materials.

![[image-1.png]]

#### Scenes
Once you've created assets, you can use those assets to build "scenes". Use the asset browser to add object as "linked" (not append) and the addon should automatically create the necessary overrides.

In this mode, you cannot edit the meshes or material sets, but you can replace the object with any object from it's variation group, and you change location/rotation/scale

When you export a scene, meshes are replaced with empties, making tiny glb files. When you import in godot mterrain asset library, empties are replaced with correct assets.

If you add the suffix "_hlod" to the root node, then when you import into mterrain in godot it will create a baker scene for you, and replace objects with the correct assets (assuming you've imported the assets correctly in godot mterrain asset library)

You can also try the asset shelf:
Save the asset blend file and add it to the blender/preferences/paths as a library.
Then start a new blend file, enable the asset shelf, and drag object from the asset shelf into the scene.

