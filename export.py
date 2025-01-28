import bpy
import os
from functools import partial
from bpy_extras.io_utils import ExportHelper
from .properties import activate_material_set
import configparser
import pathlib

class MTerrain_OT_ExportAsGLB(bpy.types.Operator, ExportHelper):
    """Export lod assets with material sets and surface names, include blend_path custom property, hide collection_instances"""
    bl_idname = "mterrain.export_as_glb"
    bl_label = "Export assets and scenes to glb"
    bl_options = {'PRESET', 'UNDO'}
    
    # ExportHelper mixin class uses this
    filename_ext = ""
        
    def execute(self, context):                        
        original_collections = {}                
        original_selection = context.selected_objects
        nothing_selected = False
        context.scene['blend_file'] = os.path.basename(bpy.data.filepath)        

        objects_to_consider = [obj for obj in context.view_layer.objects if not obj.hide_get(view_layer=context.view_layer) and obj.name in context.view_layer.objects ]

        #toggle_lods_hidden(False)
        #####################################
        ## if nothing selected, select all ##
        #####################################
        if len(context.selected_objects)==0:
            nothing_selected = True
            original_selection = objects_to_consider
            for obj in original_selection:                
                for col in obj.users_collection:
                    if col.asset_data:
                        obj.select_set(True)
        variation_groups = []        
        variation_objects_process = []
        material_to_delete = []
        objects_to_delete = []
        for obj in objects_to_consider:                   
            if not obj.name in variation_objects_process:
                variation_group = [v.name for v in obj.mesh_lods.variations]
                variation_group.append(obj.name)
                variation_objects_process += variation_group
                variation_groups.append(variation_group)
        for obj in original_selection:                               
            #######################
            # Process Collections #
            #######################     
            if obj.instance_collection and not obj.instance_collection == None:                
                if obj.instance_collection.library:
                    obj['blend_file'] = obj.instance_collection.library.name
                    original_collections[obj.name] = obj.instance_collection.name                    
                    obj.instance_collection = None
                else:
                    obj["blend_file"] = os.path.basename(bpy.data.filepath)
                    original_collections[obj.name] = obj.instance_collection.name
                    obj.instance_collection = None            
            elif obj.override_library:
                obj_name = obj.name if not "." in obj.name else obj.name.split(".")[0]                
                new_obj = bpy.data.objects.new(obj_name, None)
                context.scene.collection.objects.link(new_obj)
                new_obj.select_set(True)
                new_obj.parent = obj.parent
                new_obj.location = obj.location
                new_obj.scale = obj.scale
                new_obj.rotation_euler = obj.rotation_euler
                blend_file = obj.override_library.reference.library.name
                if not blend_file.endswith(".blend"):
                    blend_file = blend_file.split(".blend")[0] + ".blend"
                new_obj['blend_file'] = blend_file
                new_obj['active_material_set_id'] = obj.mesh_lods.active_material_set_id
                obj.select_set(False)
                objects_to_delete.append(new_obj)
                pass
                
            ########################
            # Process Mesh objects #
            ########################                            
            elif obj.type =="MESH":                  
                #use_vertex_color_for_surfaces = len(context.scene.color_palette.colors) > 0                
                # Split lod meshes into separate objects
                if len(obj.mesh_lods.lods) > 0:                    
                    obj.select_set(False)
                    for i, meshlod in enumerate(obj.mesh_lods.lods):
                        new_object_name = obj.name + "_lod_" + str(meshlod.lod)
                        new_object = bpy.data.objects.new(new_object_name, meshlod.mesh)                                                                          
                        objects_to_delete.append(new_object)

                        used_materials = set()                        
                        for poly in meshlod.mesh.polygons:
                            used_materials.add(poly.material_index)
                        new_object['surface_names'] = [m.value for i, m in enumerate(meshlod.mesh.material_sets.surface_names) if i in used_materials]                                    
                        print(new_object['surface_names'])
                        # Replace materials with temporary ones that have the correct slot names
                        for i, slot in enumerate(new_object.material_slots):            
                            if not i in used_materials: continue
                            dummy_material_name = new_object['surface_names'][i]
                            if not dummy_material_name in bpy.data.materials:
                                slot.material = bpy.data.materials.new(dummy_material_name)
                            else:
                                slot.material = bpy.data.materials[dummy_material_name]
                            if not slot.material in material_to_delete:
                                material_to_delete.append(slot.material)
                        
                        for collection in obj.users_collection:
                            collection.objects.link(new_object)
                        new_object.select_set(True)
                        
                        material_sets = []                        
                                                
                        for material_set in meshlod.mesh.material_sets.sets:
                            material_array = []
                            for slot_id, material in enumerate(material_set.materials):
                                if not slot_id in used_materials: continue
                                if material.material:
                                    material_array.append(material.material.name)
                                else:
                                    material_array.append("")
                            material_sets.append(material_array)
                        new_object['material_sets'] = material_sets                           
            
            ###########################
            # Add Tags to collections #
            ###########################
            for col in obj.users_collection:
                if col.asset_data and obj.name in col.objects:
                    obj['tags'] = [tag.name for tag in col.asset_data.tags]                 
                    break                    

        context.scene['variation_groups'] = variation_groups
        ##########
        # EXPORT #
        ##########
        bpy.ops.export_scene.gltf(
                filepath = self.filepath,
                use_active_scene = True,
                use_selection = True,
                use_visible = False,
                export_format = 'GLB',                
                export_image_format = 'NONE',
                export_materials = 'EXPORT',
                #export_colors = self.batch_export_colors,
                export_attributes=True,
                export_all_vertex_colors=True,
                export_cameras = False,
                export_extras = True,
                export_yup = True,
                export_apply = True
            )
        #############################
        # Restore original settings #
        #############################
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects_to_delete:
            bpy.data.objects.remove(obj)
        for material in material_to_delete:
            bpy.data.materials.remove(material)        
        for obj in original_selection:       
            if "blend_file" in obj:
                del obj['blend_file']
                if obj.name in original_collections:
                    obj.instance_collection = bpy.data.collections[original_collections[obj.name]]                
            if nothing_selected:
                obj.select_set(False)
            else:
                obj.select_set(True)
            if obj.type == 'MESH' and len(obj.data.material_sets.sets) > 0:
                activate_material_set(obj, obj.mesh_lods.active_material_set_id)
                            
        return {'FINISHED'}
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class MTerrain_OT_close_baker(bpy.types.Operator):
    """close baker scene"""
    bl_idname = "mterrain.close_baker_scene"
    bl_label = "Close baker scene"
    bl_options = {'PRESET', 'UNDO'}
        
    def execute(self, context): 
        context.scene.baker_path = ""
        for obj in bpy.data.objects:
            bpy.data.objects.remove(obj)
        return {'FINISHED'}

class MTerrain_OT_open_baker(bpy.types.Operator, ExportHelper):
    """Open baker scene"""
    bl_idname = "mterrain.open_baker_scene"
    bl_label = "Open baker scene for editing"
    bl_options = {'PRESET', 'UNDO'}
    filter_glob: bpy.props.StringProperty(
        default = "*.tscn", options={'HIDDEN'}
    )
    # ExportHelper mixin class uses this
    filename_ext = ".tscn"
        
    def execute(self, context): 
        config = configparser.ConfigParser()
        try:
            config.read(self.filepath)
        except:
            self.report({'ERROR'}, "Cannot open tscn - error parsing")
            return {'CANCELLED'}
        if not get_baker_script_resource_id(config):
            self.report({'ERROR'}, "Cannot open tscn - not a baker scene")
            return {'CANCELLED'}
        else:
            context.scene.baker_path = self.filepath
            update_scene_from_tscn(context.scene.baker_path)
            return {'FINISHED'}
        

class MTerrain_OT_update_scene_from_tscn(bpy.types.Operator):
    """Import tscn baker scene into blender"""
    bl_idname = "mterrain.update_scene_from_tscn"
    bl_label = "update baker scene from tscn"
    bl_options = {'PRESET', 'UNDO'}
                
    def execute(self, context):            
        if hasattr(context.scene, 'baker_path') and context.scene.baker_path != "":        
            update_scene_from_tscn(context.scene.baker_path)
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

class MTerrain_OT_update_tscn_from_scene(bpy.types.Operator):
    """Update TSCN baker scene from blender scene"""
    bl_idname = "mterrain.update_tscn_from_scene"
    bl_label = "update tscn baker scene from blender scene"
    bl_options = {'PRESET', 'UNDO'}
     
    def execute(self, context):
        if hasattr(context.scene, 'baker_path') and context.scene.baker_path != "":
            update_tscn_from_scene(context.scene.baker_path)
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

def update_scene_from_tscn(path):
    if path == "": return
    config = configparser.ConfigParser()
    config.read(path)
    node_keys = [section for section in config.sections() if section.startswith("node")]
    root = None
    # CLEANUP
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj)
        
    # BUILD TREE
    for node_key in node_keys:
        name, type, parent = parse_tscn_key(node_key)
        if parent == "": root = name
        elif parent == ".": parent = root
        else: parent = root +"/"+parent

        #CREATE OBJECT
        obj = bpy.data.objects.new(name, None)    
        bpy.context.scene.collection.objects.link(obj)
        
        if name != root:
            #CUSTOM PROPERTIES
            for prop in config[node_key]:
                obj[prop] = config[node_key][prop]

            #ASSIGN PARENT
            root_path = parent.split("/")
            if len(root_path) == 0: continue
            current_parent = None

            for i, path_step in enumerate(root_path):
                if current_parent == None: 
                    current_parent = bpy.data.objects[root]
                else:
                    current_parent = [child for child in current_parent.children if child.name == path_step][0]
            obj.parent = current_parent

    # IMPORT JOINED MESH if exists
    joined_mesh_path = path[:-5] + "_joined_mesh.glb"
    if os.path.isfile(joined_mesh_path):
        bpy.ops.import_scene.gltf(filepath = joined_mesh_path)
        joined_mesh_name = path[:-5] + "_joined_mesh"
        joined_mesh_name = os.path.splitext( os.path.basename( joined_mesh_name))[0] 
        
        bpy.data.objects[joined_mesh_name].parent = bpy.data.objects[root]
 #       print("Joined mesh exists")


def update_tscn_from_scene(baker_path):
    #OPEN ORIGINAL
    config = configparser.ConfigParser()
    config.read(baker_path)

    #IDENTIFY EXISTING NODES
    existing_nodes = {}
    existing_names = {}
    root_node = None
    node_keys = [section for section in config.sections() if section.startswith("node")]
    for node_key in node_keys:
        name, type, parent = parse_tscn_key(node_key)
        if not name in existing_names: 
            existing_names[name] = []
        if parent == "": 
            root = name
            root_node = node_key
            existing_nodes[name] = node_key
            existing_names[name].append(name)
        else:
            if parent == ".": 
                parent = root
            else: 
                parent = root +"/"+parent        
            existing_nodes[parent+"/"+name] = node_key            
            existing_names[name].append(parent+"/"+name)

    
    #REPLACE KEYS WITH NEW VALUES
    processed_nodes = []
    processed_object_paths = []
    export_joined_mesh(root, baker_path)
    for obj in bpy.context.scene.objects:
        if obj.name.startswith(root +"_joined_mesh"): continue                    
        node_name = remove_suffix(obj.name)        
        suffix_removed = node_name != obj.name
        node_to_update = None
        object_path = None
        if node_name in existing_names:
            for path in existing_names[node_name]:
                if not "/" in path:                 
                    #Skip the root
                    node_to_update = existing_nodes[node_name]
                    object_path = [obj]
                    break
                path_steps = path.split("/")
                path_steps.pop()
                last_parent = obj
                found = False
                object_path = []
                while len(path_steps) > 0:
                    last_step = path_steps.pop()
                    if not last_parent.parent or last_parent.parent.name != last_step:
                        break
                    found = True
                    object_path = [last_parent.parent] + object_path
                    last_parent = last_parent.parent
                object_path += [obj]
                if not found: continue
                node_to_update = existing_nodes[path]
                break
            

        #CREATE NEW NODE IF NECESSARY
        if node_to_update != None and not object_path in processed_object_paths:            
            processed_object_paths.append(object_path)
            processed_nodes.append(node_to_update)
        else:
            new_parent = build_tscn_path(obj, root)
            if obj.name.lower().endswith("_baker"):
                type = "Node3D"  
                obj["script"] = "ExtResource(\"" + str(get_baker_script_resource_id(config)) + "\")"
            else:
                type = "MAssetMesh" 
            
            node_to_update = "node name=\"" + obj.name + "\" type=\"" + type +  "\" parent=\"" + new_parent + "\""                    
            processed_nodes.append(node_to_update)
            config[node_to_update] = {}
        #UPDATE META
        custom_props = ["collection_id", "blend_file", "script", "joined_mesh_id"]
        for prop in custom_props:
            if prop in obj:
                config[node_to_update][prop] = str(obj[prop])

    #REMOVE KEYS THAT NO LONGER EXIST
    for node_key in node_keys:
        if node_key in processed_nodes: continue
        del config[node_key]
            
    #SAVE
    with open(baker_path, 'w') as configfile:
        config.write(configfile)

def remove_suffix(node_name):
    try: 
        float(node_name[-4:])
        if node_name[-4] == ".":
            node_name = node_name[:-4]
        else:
            node_name = node_name[:-5] #in case of four digit suffix .0001
    except:
        pass
    return  node_name

def parse_tscn_key(key):
    name = key.split("name=\"")[1].split("\"")[0]
    type = key.split("type=\"")[1].split("\"")[0]
    parent = key.split("parent=\"")[1].split("\"")[0] if "parent=\"" in key else ""
    return name, type, parent

def build_tscn_path(obj, root):
    if obj.name == root: return ""
    if obj.parent and obj.parent.name == root: return "."
    result = ""    
    current_parent = obj.parent
    while current_parent and current_parent.name != root:
        if result == "":
            result = current_parent.name
        else:
            result = current_parent.name + "/" + result
        current_parent = current_parent.parent
    return result

def get_baker_script_resource_id(config):
    node_keys = [section for section in config.sections() if section.startswith("ext_resource")]
    for node_key in node_keys:
        if "res://addons/m_terrain/asset_manager/hlod_baker.gd" in node_key:
            return node_key.split("id=\"")[1].split("\"")[0]

def export_joined_mesh(root,baker_path):
    for obj in bpy.context.scene.objects:
        if obj.name.startswith(root +"_joined_mesh"):
            if obj.name.endswith("_joined_mesh"):
                joined_mesh_path = baker_path[:-5] + "_joined_mesh.glb"
                original_selection = {}
                for obj in bpy.context.view_layer.objects:
                    original_selection[obj] = obj.select_get()
                    obj.select_set(obj.name.startswith(root +"_joined_mesh"))
                
                bpy.ops.export_scene.gltf(
                    filepath = joined_mesh_path,
                    use_active_scene = True,
                    use_selection = True,
                    use_visible = False,
                    export_format = 'GLB',                
                    export_image_format = 'NONE',
                    export_materials = 'EXPORT',
                    #export_colors = self.batch_export_colors,
                    export_attributes=True,
                    export_all_vertex_colors=True,
                    export_cameras = False,
                    export_extras = True,
                    export_yup = True,
                    export_apply = True
                )
                for obj in original_selection:
                    obj.select_set(original_selection[obj])
                    