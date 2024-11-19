
bl_info = {
    "name": "MTerrain Helper",    
    "category": "Object",
}

import bpy
import os
from functools import partial
from bpy_extras.io_utils import ExportHelper
from .asset_shelf import MTerrain_AST_Asset_Picker, OBJECT_OT_drag_drop_asset
from .export import MTerrain_OT_ExportAsGLB
from .properties import *


class MTerrain_OT_Convert_Selected_Objects_To_Assets(bpy.types.Operator):
    bl_idname = "mterrain.convert_selected_to_assets"
    bl_label = "Convert selected objects to assets"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(self, context):
        return len(context.selected_objects) > 0

    def execute(self, context):        
        for obj in context.selected_objects:
            #TODO: Add LOD combining logic here first...
            col = None 
            col_name = obj.name
            if "_lod" in col_name:
                col_name = col_name.split("_lod")[0]
            if not col_name in bpy.data.collections:
                col = bpy.data.collections.new(col_name)
            else:
                col = bpy.data.collections[col_name]
            if not obj.name in context.scene.collection.children:
                context.scene.collection.children.link( col )
            col.objects.link(obj)
            if obj.name in context.scene.collection.objects:
                context.scene.collection.objects.unlink(obj)
            col.instance_offset = obj.location
            col.asset_mark()
            col.asset_generate_preview()
        return {"FINISHED"}

# class MTerrain_OT_Toggle_Lods_Hidden(bpy.types.Operator):
#     bl_idname = "mterrain.toggle_lods_hidden"
#     bl_label = "Toggle Hidden for Lods that are not lod0"
#     bl_description = ""
#     bl_options = {"REGISTER", "UNDO"}

#     def execute(self, context):                
#         if not "mterrain_lods_hidden" in context.scene:
#             context.scene['mterrain_lods_hidden'] = False
#         else:
#             context.scene['mterrain_lods_hidden'] = not context.scene['mterrain_lods_hidden']
#         toggle_lods_hidden(context.scene['mterrain_lods_hidden'])    
#         return {"FINISHED"}

# def toggle_lods_hidden(toggle_on):    
#     for obj in bpy.data.objects:     
#         obj.mesh_lods.active_lod = 
#         if "joined_mesh" in obj.name:
#             obj.hide_viewport = toggle_on           
#         elif "_lod" in obj.name:
#             if obj.name != get_first_lod(obj.name):
#                 obj.hide_viewport = toggle_on
#             else:
#                 obj.hide_viewport = False

class MTerrain_OT_Fix_Collection_Offsets(bpy.types.Operator):
    bl_idname = "mterrain.fix_collection_offsets"
    bl_label = "Fix Collection Offsets so that center is at lod 0"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):                        
        for col in context.view_layer.layer_collection.collection.children_recursive:            
            if not col.asset_data:                 
                continue
            single = None
            for obj in col.objects:                
                if obj.parent == None and not single:                    
                    single = obj
                elif obj.parent == None and single:                    
                    single = None
                    break
            if single != None:
                print("col: ", col.name, " SINGLE OBJECT: ", single.name, " at location: ", single.location)
                col.instance_offset = single.location
            else:
                print("col: ", col.name, " MULTI OBJECT")
                for obj in col.objects:
                    if "lod" in obj.name:
                        first_lod = bpy.data.objects[ get_first_lod(obj.name) ]
                        col.instance_offset = first_lod.location
                        break
        return {"FINISHED"}
    

def get_first_lod(name):
    data = name.split("lod")
    names = [obj_name for obj_name in bpy.data.objects.keys() if data[0] in obj_name]
    return names[0]

########
## UI ##
########
class MTerrain_PT_Tool(bpy.types.Panel):
    bl_label = 'MTerrain'
    bl_idname = 'mterrain.panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'    
    bl_context = ''
    bl_category = 'Tool'
    bl_order = 0
    bl_ui_units_x=0
    @classmethod    
    def poll(self, context):
        return context.object and context.object.type == 'MESH'
    def draw(self, context):
        layout = self.layout                        
        layout.operator(MTerrain_OT_ExportAsGLB.bl_idname, text='Export')          
        layout.separator()
        #layout.operator(MTerrain_OT_Fix_Collection_Offsets.bl_idname, text="fix collection offset")                
        if not context.selected_objects or len(context.selected_objects) == 0: return        
        #layout.operator(MTerrain_OT_Convert_Selected_Objects_To_Assets.bl_idname, text="Convert selected to asset collections")
        obj = context.object

        if len(obj.mesh_lods.lods) == 0:
            layout.operator(OBJECT_OT_convert_to_lod_object.bl_idname, text="Convert to Lod object")
        else:              
            col = layout.column(align=True)
            row = col.row()
            row.alignment = 'CENTER'        
            row.prop(obj.mesh_lods, "lods_editable", text="", toggle=1, icon="LOCKED", invert_checkbox=True)  
            
            row.label(text="Mesh Lods")                                   
            row.prop(obj.mesh_lods, "lods_editable", text="", toggle=1, icon="LOCKED", invert_checkbox=True)  
            lods = [lod for lod in obj.mesh_lods.lods]         
            lods.sort(key=lambda x: x.lod)        
            col.separator()
            for mesh_lod in lods:                        
                icon = "CHECKBOX_DEHLT" 
                if mesh_lod.lod == obj.mesh_lods.active_lod:
                    icon = "CHECKBOX_HLT"
                    if obj.data != mesh_lod.mesh:
                        bpy.app.timers.register(partial(validate_active_lod, obj), first_interval=0.01)
                        return
                row = col.row(align=True)
                if obj.mesh_lods.lods_editable:                            
                    split = row.split(factor=0.7, align=True)
                    split.operator(OBJECT_OT_activate_lod.bl_idname, text="Lod " + str(mesh_lod.lod), icon=icon).lod = mesh_lod.lod                                        
                    split.prop(mesh_lod, "lod", text="")                
                    row.context_pointer_set("lod_dictionary", mesh_lod)                                
                    op = row.operator(OBJECT_OT_remove_mesh_lod.bl_idname, icon="REMOVE", text="")                                
                else:                    
                    row.operator(OBJECT_OT_activate_lod.bl_idname, text="Lod " + str(mesh_lod.lod), icon=icon).lod = mesh_lod.lod                                        
            if obj.mesh_lods.lods_editable:                                                                                        
                op = col.operator(OBJECT_OT_add_lod.bl_idname, icon="ADD", text="")              
            
            row = layout.row()
            row.alignment = 'CENTER'       
            if obj.mesh_lods.lods_editable:                             
                row.label(text="Import Lod From Object")      
                layout.prop(obj.mesh_lods, "object_for_replacing_lod_mesh", text="", )
            layout.separator(type="LINE")

            if obj.mesh_lods.lods_editable:
                row = layout.row()
                row.alignment = 'CENTER'                  
                row.label(text="Surface Names")                            

                col = layout.column(align=True)
                if len(obj.data.material_sets.surface_names) != len(obj.data.materials):                
                    bpy.app.timers.register(partial(validate_surface_count, obj.data), first_interval=0.01)
                    return
                for i, surface_name in enumerate(obj.data.material_sets.surface_names):                
                    row = col.row()                    
                    row.prop(surface_name, "value", text="") #str(i))                
                    row.operator(OBJECT_OT_RemoveNamedSurface.bl_idname, icon="REMOVE", text="").surface_id = i                
                layout.operator(OBJECT_OT_AddNamedSurface.bl_idname, icon="ADD", text="")
                layout.separator()
            col = layout.column(align=True)        
            row = col.row()
            row.alignment = 'CENTER'
            row.prop(obj.mesh_lods, "material_sets_editable", text="", toggle=1, icon="LOCKED", invert_checkbox=True)  
            row.label(text="Material Sets")
            row.prop(obj.mesh_lods, "material_sets_editable", text="", toggle=1, icon="LOCKED", invert_checkbox=True)              
            col.separator()
            for set_id, material_set in enumerate(obj.data.material_sets.sets):                
                if len(material_set.materials) != len(obj.data.materials):
                    bpy.app.timers.register(partial(validate_material_set_materials, obj.data, material_set), first_interval=0.01)                   
                    return
                #header, panel = layout.panel("material_set_" + str(i))
                row = col.row()
                icon = "CHECKBOX_DEHLT" 
                if set_id == obj.mesh_lods.active_material_set:
                    icon = "CHECKBOX_HLT"
                    if obj.data.materials.values() != [mat.material for mat in material_set.materials]:
                        bpy.app.timers.register(partial(validate_active_material_set, obj), first_interval=0.01)                                    
                if obj.mesh_lods.material_sets_editable:
                    col.separator()                    
                    row.operator(OBJECT_OT_ActivateMaterialSet.bl_idname, text="", icon=icon).set_id = set_id
                    row.prop(material_set, "name", text="")
                else:
                    row.operator(OBJECT_OT_ActivateMaterialSet.bl_idname, text=material_set.name, icon=icon).set_id = set_id
                if obj.mesh_lods.material_sets_editable:
                    row.operator(OBJECT_OT_RemoveMaterialSet.bl_idname, icon="REMOVE", text="").set_id = set_id

                for surface_id, material in enumerate(material_set.materials):                                              
                    row = col.row()
                    # if material.material != obj.data.materials[surface_id]:
                    #     bpy.app.timers.register(partial(validate_material_sets, obj), first_interval=0.01)                       
                    #     return
                    if obj.mesh_lods.material_sets_editable:
                        row.prop(material, "material", text= obj.data.material_sets.surface_names[surface_id].value)                    
                if obj.mesh_lods.material_sets_editable:
                    col.separator()
            if obj.mesh_lods.material_sets_editable:
                layout.operator(OBJECT_OT_AddMaterialSet.bl_idname, icon="ADD", text="")
            
            #layout.label(text=str(obj.material_sets.sets))
            #for idx, array in enumerate(obj.material_sets.sets):          
                #layout.label(text=str(array))
                #layout.prop(array, "material", text=str(idx))
            # for idx, array in enumerate(obj.material_sets.sets):
            #     box = layout.box()
            #     row = box.row()
            #     row.label(text=f"Set {idx+1}")
            #     row.operator("object.add_material_to_array", text="Add Material").array_index = idx

            #     # Display materials in the sub-array
            #     for mat_idx, mat_wrapper in enumerate(array.material_array):
            #         mat_row = box.row()
            #         mat_row.prop(mat_wrapper, "material", text=f"Material {mat_idx+1}")
            #         mat_row.operator("object.remove_material_from_array", text="", icon="X").index = (idx, mat_idx)

#################
# Material Sets #
#################
class OBJECT_OT_AddNamedSurface(bpy.types.Operator):
    bl_idname = "object.add_named_surface_to_mesh"
    bl_label = "Add named surface to mesh"
    @classmethod 
    def poll(self, context):
        return context.object and not context.object.override_library

    def execute(self, context):
        add_named_surface_to_object(context.object)
        return {'FINISHED'}

class OBJECT_OT_RemoveNamedSurface(bpy.types.Operator):
    bl_idname = "object.remove_named_surface"
    bl_label = "Remove named surface for object"
    
    surface_id: bpy.props.IntProperty()
    @classmethod 
    def poll(self, context):
        return context.object and not context.object.override_library and len(context.object.data.material_sets.surface_names) >1
    def execute(self, context):        
        remove_named_surface(context.object.data, self.surface_id)
        return {'FINISHED'}

def add_named_surface_to_object(obj):
    ##Ensure each mesh has the same number of surfaces as surface_names    
    count = len(obj.data.material_sets.surface_names) - len(obj.data.materials)
    for i in range(abs(count)):
        if count > 0:
            obj.data.materials.append(None)            
        else:                    
            add_named_surface_to_mesh(obj.data)            
    add_named_surface_to_mesh(obj.data)
    
def add_named_surface_to_mesh(mesh):
    mesh.material_sets.surface_names.add()        
    mesh.material_sets.surface_names[-1].value = "surface"    
    surface_count = len(mesh.material_sets.surface_names)
    for material_set in mesh.material_sets.sets:
        for i in range(abs(len(material_set.materials) - surface_count)):            
            if len(material_set.materials) < surface_count:            
                material_set.materials.add()
            else:
                material_set.materials.remove(material_set.materials[-1])    
    for i in range(abs(len(mesh.materials) - surface_count)):
        if len(mesh.materials) < surface_count:
            mesh.materials.append(None)

def remove_named_surface(mesh, surface_id):
    if surface_id == -1:
        surface_id = len(mesh.material_sets.surface_names)-1
    mesh.material_sets.surface_names.remove(surface_id)    
    for material_set in mesh.material_sets.sets:
        material_set.materials.remove(surface_id)            
    mesh.materials.pop(index=surface_id)

class OBJECT_OT_AddMaterialSet(bpy.types.Operator):
    bl_idname = "object.add_material_set"
    bl_label = "Add Material to Array"
    @classmethod 
    def poll(self, context):
        return context.object and len(context.object.data.material_sets.sets) < 126 and not context.object.override_library

    def execute(self, context):                
        add_material_set(context.object)
        return {'FINISHED'}

class OBJECT_OT_RemoveMaterialSet(bpy.types.Operator):
    bl_idname = "object.remove_material_set"
    bl_label = "Remove Material set"

    set_id: bpy.props.IntProperty()
    @classmethod
    def poll(self, context):
        return context.object and not context.object.override_library and context.object.mesh_lods.material_set_count > 1

    def execute(self, context):
        obj = context.object        
        remove_material_set(obj, self.set_id)
        return {'FINISHED'}

def add_material_set(obj):
    obj.mesh_lods.material_set_count += 1 
    for lod in obj.mesh_lods.lods:                           
        lod.mesh.material_sets.sets.add()                
        while len(lod.mesh.material_sets.sets[-1].materials) < len(lod.mesh.material_sets.surface_names):
            lod.mesh.material_sets.sets[-1].materials.add()

def remove_material_set(obj, set_id):
    for lod in obj.mesh_lods.lods:
        lod.mesh.material_sets.sets.remove(set_id)    
    obj.mesh_lods.material_set_count -= 1
        

class OBJECT_OT_ActivateMaterialSet(bpy.types.Operator):
    bl_idname = "object.activate_material_set"
    bl_label = "Activate material set for object"
    
    set_id: bpy.props.IntProperty()
    @classmethod
    def poll(self, context):
        return context.object
    
    def execute(self, context):        
        activate_material_set(context.object, self.set_id)
        return {'FINISHED'}
      
############
# MESH LOD #
############
class OBJECT_OT_convert_to_lod_object(bpy.types.Operator):
    bl_idname = "object.convert_to_lod_object"
    bl_label = "Convert object to lod"
    @classmethod
    def poll(self, context):
        return context.object and not context.object.override_library

    def execute(self, context):                
        for obj in context.selected_objects:
            lod = obj.mesh_lods.lods.add()        
            obj.mesh_lods.lod_count += 1                        
            lod.mesh = obj.data.copy()
            lod.mesh.use_fake_user = True
            if len(obj.data.material_sets.sets) == 0:                
                add_material_set(obj)
            if not "_lod_" in lod.mesh.name:
                lod.mesh.name = obj.name + "_lod_0"
                lod.lod = 0
            else:
                lod.lod = int(lod.mesh.name.split("_lod_")[1])
                lod.mesh.name = obj.name + "_lod_" + str(lod.lod)
            
            #materials = [mat for mat in lod.mesh.materials]                        
            validate_material_set_materials(lod.mesh, lod.mesh.material_sets.sets[0] )
            for i in range(max(1, len(lod.mesh.materials))):
                add_named_surface_to_mesh(lod.mesh)                     
                lod.mesh.material_sets.sets[0].materials[i].material = lod.mesh.materials[i]                
            with context.temp_override(object = obj):
                bpy.ops.object.activate_mesh_lod(lod = lod.lod)
                
        return {'FINISHED'}

class OBJECT_OT_add_lod(bpy.types.Operator):
    bl_idname = "object.add_mesh_lod"
    bl_label = "add mesh lod for object"

    @classmethod
    def poll(self, context):
        return context.object and not context.object.override_library and context.object.mesh_lods.lods_editable

    def execute(self, context):        
        all_lod = [m.lod for m in context.object.mesh_lods.lods]        
        lod = context.object.mesh_lods.lods.add()        
        lod.lod = max(all_lod) + 1                        
        lod.mesh = context.object.data.copy()
        lod.mesh.use_fake_user = True
        lod.mesh.name = context.object.name + "_lod_" + str(lod.lod)
        context.object.mesh_lods.lod_count += 1
        bpy.ops.object.activate_mesh_lod(lod = lod.lod)        
        return {'FINISHED'}

class OBJECT_OT_remove_mesh_lod(bpy.types.Operator):
    bl_idname = "object.remove_mesh_lod"
    bl_label = "remove mesh lod for object"    
    
    @classmethod
    def poll(self, context):
        return context.object and not context.object.override_library and len(context.object.mesh_lods.lods) >1
  
    def execute(self, context):              
        lod = context.lod_dictionary.lod   
        if not context.object.type == 'MESH': return {'CANCELLED'}        
        context.object.mesh_lods.lod_count -= 1
        if lod == context.object.mesh_lods.active_lod:
            all_lod = [x.lod for x in context.object.mesh_lods.lods]
            all_lod.sort()
            new_index = all_lod.index(lod) -1
            if new_index == -1:
                new_index = 1                                        
            set_active_lod(context.object, all_lod[new_index])            
        
        if context.lod_dictionary.mesh:
            bpy.data.meshes.remove(context.lod_dictionary.mesh)                         
        for i, lod_item in enumerate(context.object.mesh_lods.lods):
            if lod_item == context.lod_dictionary:
                context.object.mesh_lods.lods.remove(i)
                break                
        return {'FINISHED'}

class OBJECT_OT_activate_lod(bpy.types.Operator):
    bl_idname = "object.activate_mesh_lod"
    bl_label = "Activate mesh lod for object"
    lod: bpy.props.IntProperty()
    
    @classmethod
    def poll(self, context):
        return True #not context.object.library

    def execute(self, context):
        set_active_lod(context.object, self.lod)        
        return {'FINISHED'}

def depsgraph_update_post(scene):        
    old_object_names = scene.scene_objects.split(",")    
    object_names = [obj.name for obj in scene.objects]
    #removed = [o for o in old_object_names if not o in object_names]
    added = [o for o in object_names if not o in old_object_names]    
    for object_name in added:
        obj = bpy.data.objects[object_name]
        if obj.is_property_readonly("location"):            
            new_obj = obj.override_create()
            scene.collection.objects.link(new_obj)
            for lod in new_obj.mesh_lods.lods:
                lod.mesh = lod.mesh.override_create()                        
            scene.collection.objects.unlink(obj)
            set_active_lod(new_obj, 0)            
    scene.scene_objects = ",".join(object_names)  


classes= []
props = []

def register():
    classes = [        
        MeshLod,
        MeshLods,
        OBJECT_OT_convert_to_lod_object,
        OBJECT_OT_add_lod,
        OBJECT_OT_remove_mesh_lod,
        OBJECT_OT_activate_lod,
        StringItem,
        MaterialItem,
        MaterialSet,
        MaterialSets,        
        MTerrain_OT_ExportAsGLB, 
        #MTerrain_OT_Toggle_Lods_Hidden, 
        MTerrain_OT_Convert_Selected_Objects_To_Assets, 
        MTerrain_OT_Fix_Collection_Offsets, 
        MTerrain_PT_Tool,        
        
        OBJECT_OT_AddNamedSurface,
        OBJECT_OT_RemoveNamedSurface,
        OBJECT_OT_AddMaterialSet,
        OBJECT_OT_RemoveMaterialSet,
        OBJECT_OT_ActivateMaterialSet,

        MTerrain_AST_Asset_Picker,      
        OBJECT_OT_drag_drop_asset
    ]                
    for c in classes:
        bpy.utils.register_class(c)    
    
    bpy.types.WorkSpace.selected_asset = bpy.props.IntProperty(
        name="selected_asset", default=0         
    )       
    bpy.types.Scene.scene_objects = bpy.props.StringProperty()
    bpy.types.Mesh.material_sets = bpy.props.PointerProperty(type=MaterialSets) 
    bpy.types.Object.mesh_lods = bpy.props.PointerProperty(type=MeshLods)         
    props = [bpy.types.WorkSpace.selected_asset, bpy.types.Mesh.material_sets, bpy.types.Scene.scene_objects]
    #bpy.types.ASSETSHELF_PT_display.append(MTerrain_PT_Tool.draw)
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_post)

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)    

    for prop in props:
        del prop
    #bpy.types.ASSETSHELF_PT_display.remove(MTerrain_PT_Tool.draw)
    bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_post)    
if __name__ == "__main__":
    register()

#TODO:
# - changes to material slots should update UI
# - 