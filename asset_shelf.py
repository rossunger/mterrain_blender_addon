import bpy
import os
from functools import partial
from bpy_extras.io_utils import ExportHelper

class OBJECT_OT_drag_drop_asset(bpy.types.Operator):
    bl_idname = "object.drag_drop_asset"
    bl_label = "Drag and Drop Object"
    bl_description = "Drag and drop an object into the 3D viewport"

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value=='RELEASE':            
            print("\n\n\nMOdal finished")
            print(context.asset_library_reference.items)
            print(context.active_file)
        #execute(self, context)
            return {'FINISHED'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):                         
        try:
            bpy.ops.wm.link(
                filepath=asset_filepath,
                directory=asset_directory,
                filename=self.asset_name,
                link=True
            )
            self.report({'INFO'}, f"Linked {self.asset_type}: {self.asset_name}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to link asset: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}

class MTerrain_AST_Asset_Picker(bpy.types.AssetShelf):
    # label is displayed at the center of the pie menu.
    bl_space_type = 'VIEW_3D'
    bl_idname = "mterrain.asset_picker"
    bl_options = {'DEFAULT_VISIBLE', 'STORE_ENABLED_CATALOGS_IN_PREFERENCES', 'NO_ASSET_DRAG'}
    bl_activate_operator = "OBJECT_OT_drag_drop_asset"     
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
        # Replace with the actual library path
        library_path = "/path/to/your/library.blend"

        # Determine asset type (Object or Collection)
        asset_type = "OBJECT" if asset.type == "MESH" else "COLLECTION"

        op = layout.operator(
            OBJECT_OT_drag_drop_asset.bl_idname,
            text=f"Link {asset.name} ({asset_type}) to Scene"
        )
        op.library_path = library_path
        op.asset_name = asset.name
        op.asset_type = asset_type
