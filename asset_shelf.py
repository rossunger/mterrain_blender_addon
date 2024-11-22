import bpy
import os
from functools import partial
from bpy_extras.io_utils import ExportHelper

class OBJECT_OT_drag_drop_asset(bpy.types.Operator):
    bl_idname = "mterrain.drag_drop_asset"
    bl_label = "Drag and Drop Object"
    bl_description = "Drag and drop an object into the 3D viewport"    

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value=='RELEASE':                                    
            with bpy.data.libraries.load(context.asset.full_library_path, assets_only = True, link = True) as (data_from, data_to):
                for i, obj in enumerate(data_from.objects):                
                    if obj == context.asset.name:
                        data_to.objects.append(data_from.objects[i])                
                        print(obj)
            for obj in data_to.objects:
                print(obj)
                #bpy.context.scene.collection.objects.link(obj)
            return {'FINISHED'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):        
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    #def execute(self, context):   
     #   print("EXECUTING MODAL")  
        #context.asset.full_library_path
        
        #return {'FINISHED'}

class MTerrain_AST_Asset_Picker(bpy.types.AssetShelf):
    # label is displayed at the center of the pie menu.
    bl_space_type = 'VIEW_3D'
    bl_idname = "mterrain.asset_picker"
    bl_options = {'DEFAULT_VISIBLE', 'STORE_ENABLED_CATALOGS_IN_PREFERENCES' } #, 'NO_ASSET_DRAG'}
    asset_library_reference = {"ALL"}
    #bl_activate_operator = "mterrain_OT_drag_drop_asset"     
    #bl_activate_operator = MTerrain_OT_Toggle_Lods_Hidden.bl_idname
    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    @classmethod
    def asset_poll(cls, asset):
        return True #asset.id_type in {'Collection'}

    @classmethod
    def draw_context_menu(cls, context, asset, layout):
        if not asset or not asset.asset_data:
            return        
        
