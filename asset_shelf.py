import bpy
import os
from functools import partial
from bpy_extras.io_utils import ExportHelper
class OBJECT_OT_drag_drop_asset(bpy.types.Operator):
    bl_idname = "object.drag_drop_asset"
    bl_label = "Drag and Drop Object"
    bl_description = "Drag and drop an object into the 3D viewport"

    # This will hold the data being dragged (e.g., object name or filepath)
    dragged_data: bpy.props.StringProperty()

    def execute(self, context):
        # Process the dragged data (e.g., add an object to the scene)
        if self.dragged_data:
            print(f"Dropped data: {self.dragged_data}")
            # Example: Create a cube and name it based on the dragged data
            bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
            obj = context.active_object
            obj.name = self.dragged_data
        return {'FINISHED'}



class MTerrain_AST_Asset_Picker(bpy.types.AssetShelf):
    # label is displayed at the center of the pie menu.
    bl_space_type = 'VIEW_3D'
    bl_idname = "mterrain.asset_picker"
    bl_options = {'DEFAULT_VISIBLE', 'STORE_ENABLED_CATALOGS_IN_PREFERENCES'}
    #bl_activate_operator = MTerrain_OT_Toggle_Lods_Hidden.bl_idname
    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    @classmethod
    def asset_poll(cls, asset):
        return True #asset.id_type in {'Collection'}

    @classmethod
    def draw_context_menu(cls, context, asset, layout):
        layout.operator("object.drag_drop_asset", text="Drag Cube").dragged_data = "Cube_Data"