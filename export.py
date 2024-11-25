import bpy
import os
from functools import partial
from bpy_extras.io_utils import ExportHelper
from .properties import activate_material_set
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
        #toggle_lods_hidden(False)
        #####################################
        ## if nothing selected, select all ##
        #####################################
        if len(context.selected_objects)==0:
            nothing_selected = True
            original_selection = context.scene.objects
            for obj in original_selection:                
                for col in obj.users_collection:
                    if col.asset_data:
                        obj.select_set(True)
        variation_groups = []        
        variation_objects_process = []
        material_to_delete = []
        objects_to_delete = []
        for obj in context.scene.objects:                   
            if not obj.name in variation_objects_process:
                variation_group = [v.name for v in obj.mesh_lods.variations]
                variation_group.append(obj.name)
                variation_objects_process += variation_group
                variation_groups.append(variation_group)
        for obj in context.scene.objects:                               
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
                new_obj.select_set(True)
                new_obj['blend_file'] = obj.override_library.reference.library.name
                new_obj['active_material_set_id'] = obj.mesh_lods.active_material_set_id
                obj.select_set(false)
                objects_to_delete.append(new_obj)
                pass
                
            ########################
            # Process Mesh objects #
            ########################                            
            elif obj.type =="MESH":                                             
                # Split lod meshes into separate objects
                if len(obj.mesh_lods.lods) > 0:                    
                    obj.select_set(False)
                    for i, meshlod in enumerate(obj.mesh_lods.lods):
                        new_object_name = obj.name + "_lod_" + str(meshlod.lod)
                        new_object = bpy.data.objects.new(new_object_name, meshlod.mesh)                                                  
                        #new_object.parent = obj.parent
                        objects_to_delete.append(new_object)
                        # Replace materials with temporary ones that have the correct slot names
                        for i, slot in enumerate(new_object.material_slots):            
                            dummy_material_name = new_object.data.material_sets.surface_names[i].value
                            if not dummy_material_name in bpy.data.materials:
                                slot.material = bpy.data.materials.new(new_object.data.material_sets.surface_names[i].value)
                            else:
                                slot.material = bpy.data.materials[dummy_material_name]
                            if not slot.material in material_to_delete:
                                material_to_delete.append(slot.material)
                        
                        for collection in obj.users_collection:
                            collection.objects.link(new_object)
                        new_object.select_set(True)

                        new_object['surface_names'] = [m.value for m in meshlod.mesh.material_sets.surface_names]
                        material_sets = []                        
                        for material_set in meshlod.mesh.material_sets.sets:
                            material_array = []
                            for material in material_set.materials:
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
            if obj.type == 'MESH':
                activate_material_set(obj, obj.mesh_lods.active_material_set_id)
                            
        return {'FINISHED'}
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

