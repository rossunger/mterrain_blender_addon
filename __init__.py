
bl_info = {
    "name": "MTerrain Helper",    
    "category": "Object",
}

import bpy
import os
from functools import partial
from bpy_extras.io_utils import ExportHelper
from .asset_shelf import *
from .export import *
from .properties import *
from.autotile import MTerrain_OT_convert_tilemap_to_instances, MTerrain_OT_prepare_tilemap_for_painting
import mathutils
import gpu
from gpu_extras.batch import batch_for_shader
import bmesh

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
def draw_color_button(layout, operator_idname, color=(0.,0.,0.,1.)):
    row = layout.row(align=True)
    row.scale_y = 2.0
    op = row.operator(operator_idname, text="", emboss=False)

    def draw_callback():
        region = bpy.context.region
        shader = gpu.shader.from_builtin('FLAT_COLOR')
        verts = [(0,0),(0,50), (100,50), (100,0)]
        indices = [(0,1,2), (2,3,0)]
        batch = batch_for_shader(shader,'TRIS', {"pos":verts, "color": color}, indices=indices)
        shader.bind()
        #shader.uniform_float("color", color)
        batch.draw(shader)
    bpy.types.SpaceView3D.draw_handler_add(draw_callback, (), "WINDOW", "POST_PIXEL")

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
        return True #context.object and context.object.type == 'MESH'

    def draw(self, context):
        layout = self.layout                        
        layout.operator(MTerrain_OT_ExportAsGLB.bl_idname, text='Export')          
        layout.separator()
        #layout.operator(MTerrain_OT_Fix_Collection_Offsets.bl_idname, text="fix collection offset")                
        if not context.object or not context.selected_objects or len(context.selected_objects) == 0: 
            layout.operator(MTerrain_OT_prepare_tilemap_for_painting.bl_idname, text = "Make Tilemap")
            if False:
                layout.operator(MTerrain_OT_convert_tilemap_to_instances.bl_idname, text = "Make Building")
            return        
        #layout.operator(MTerrain_OT_Convert_Selected_Objects_To_Assets.bl_idname, text="Convert selected to asset collections")
        obj = context.object        
        if context.selected_objects and len(context.selected_objects)>1:
            layout.operator(OBJECT_OT_merge_variations.bl_idname, text="Merge variation groups")
        if len(obj.mesh_lods.lods) == 0:
            layout.operator(OBJECT_OT_convert_to_lod_object.bl_idname, text="Convert to Lod object")
        else:                      
            build_variations_layout(layout, obj)                                    
            build_lod_layout(layout,obj)                
            build_material_sets_layout(layout, obj)
        
        if not "face_color" in context.object.data.color_attributes:
            layout.separator()            
            layout.operator(OBJECT_OT_Make_Palette_Material.bl_idname, text="Create Color Palette Material")
        else:
            layout.separator()            
            col = layout.column()
            row = col.row()
            row.label(text="Color Palette")
            row.prop(context.scene.color_palette, "edit_locked", text="", icon="LOCKED")
            grid = col.grid_flow(columns = 8, align=True)                                                            
            for i, color in enumerate(context.scene.color_palette.colors):
                #box.operator(OBJECT_OT_update_color_in_palette.bl_idname, )                
                if context.scene.color_palette.edit_locked:                                          
                    op = grid.operator(OBJECT_OT_Set_Face_Color.bl_idname, text="", icon_value=color.icon_id, emboss=True)
                    op.color = color.color
                    
                else:                    
                    row = col.row(align=True)
                    row.prop(color, "name", text="")
                    row.prop(color, "color", text="")
            col.operator(OBJECT_OT_add_color_to_palette.bl_idname, text="", icon="ADD")
            #layout.label(text=str(obj.material_sets.sets))
            #for idx, array in enumerate(obj.material_sets.sets):          
                #layout.label(text=str(array))
                #layout.prop(array, "material", text=str(idx))
            # for idx, array in enumerate(obj.material_sets.sets):
            #     box = layout.box()
            #     row = box.row()
            #     row.label(text=f"Set {idx+1}")
            #     row.operator("mterrain.add_material_to_array", text="Add Material").array_index = idx

            #     # Display materials in the sub-array
            #     for mat_idx, mat_wrapper in enumerate(array.material_array):
            #         mat_row = box.row()
            #         mat_row.prop(mat_wrapper, "material", text=f"Material {mat_idx+1}")
            #         mat_row.operator("mterrain.remove_material_from_array", text="", icon="X").index = (idx, mat_idx)

def build_lod_layout(layout, obj):
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
        if obj.mesh_lods.lods_editable and not obj.override_library and not obj.library:                            
            split = row.split(factor=0.7, align=True)
            split.operator(OBJECT_OT_activate_lod.bl_idname, text="Lod " + str(mesh_lod.lod), icon=icon, depress=mesh_lod.lod==obj.mesh_lods.active_lod).lod = mesh_lod.lod                                        
            split.prop(mesh_lod, "lod", text="")                
            row.context_pointer_set("lod_dictionary", mesh_lod)                                
            op = row.operator(OBJECT_OT_remove_mesh_lod.bl_idname, icon="REMOVE", text="")                                
        else:                    
            row.operator(OBJECT_OT_activate_lod.bl_idname, text="Lod " + str(mesh_lod.lod), icon=icon, depress=mesh_lod.lod==obj.mesh_lods.active_lod).lod = mesh_lod.lod                                        
    if obj.mesh_lods.lods_editable and not obj.override_library and not obj.library:                                                                                        
        op = col.operator(OBJECT_OT_add_lod.bl_idname, icon="ADD", text="")              
    
    row = layout.row()
    row.alignment = 'CENTER'       
    if obj.mesh_lods.lods_editable and not obj.override_library and not obj.library:                             
        row.label(text="Import Lod From Object")      
        layout.prop(obj.mesh_lods, "object_for_replacing_lod_mesh", text="", )
    layout.separator(type="LINE")

    if obj.mesh_lods.lods_editable and not obj.override_library and not obj.library:
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

def build_material_sets_layout(layout, obj):
    col = layout.column(align=True)        
    row = col.row()
    row.alignment = 'CENTER'
    can_edit = obj.mesh_lods.material_sets_editable 
    is_instance = obj.library or obj.override_library
    if not is_instance:
        row.prop(obj.mesh_lods, "material_sets_editable", text="", toggle=1, icon="LOCKED", invert_checkbox=True)  
        row.label(text="Material Sets")
        row.prop(obj.mesh_lods, "material_sets_editable", text="", toggle=1, icon="LOCKED", invert_checkbox=True)              
        col.separator()
        for material_set in obj.data.material_sets.sets:
            set_id = material_set.material_set_id                
            if len(material_set.materials) != len(obj.data.materials):
                bpy.app.timers.register(partial(validate_material_set_materials, obj.data, material_set), first_interval=0.01)                   
                return
            #header, panel = layout.panel("material_set_" + str(i))
            row = col.row(align=True)
            icon = "CHECKBOX_DEHLT" 
            if set_id == obj.mesh_lods.active_material_set_id:
                icon = "CHECKBOX_HLT"
                if obj.data.materials.values() != [mat.material for mat in material_set.materials]:
                    bpy.app.timers.register(partial(validate_active_material_set, obj), first_interval=0.01)                                    
            if can_edit:
                #col.separator()                    
                row.context_pointer_set("obj", obj)
                op = row.operator(OBJECT_OT_ActivateMaterialSet.bl_idname, text="", depress=set_id == obj.mesh_lods.active_material_set_id, icon=icon)
                op.set_id = set_id                    
                row.prop(material_set, "name", text="")                        
                row.operator(OBJECT_OT_RemoveMaterialSet.bl_idname, icon="REMOVE", text="").set_id = set_id
                for surface_id, material in enumerate(material_set.materials):                                              
                    row = col.row()                                
                    row.prop(material, "material", text= obj.data.material_sets.surface_names[surface_id].value)                                
                col.separator()
            else:
                row.context_pointer_set("obj", obj)
                op = row.operator(OBJECT_OT_ActivateMaterialSet.bl_idname, text=material_set.name, depress=set_id == obj.mesh_lods.active_material_set_id)                
                op.set_id = set_id                    
        if can_edit:
            layout.operator(OBJECT_OT_AddMaterialSet.bl_idname, icon="ADD", text="")
    else:
        row.label(text="Material Sets")
        for material_set in obj.data.material_sets.sets:
            set_id = material_set.material_set_id           
            row = col.row(align=True)    
            row.context_pointer_set("obj", obj)
            op = row.operator(OBJECT_OT_ActivateMaterialSet.bl_idname, text=material_set.name, depress=set_id == obj.mesh_lods.active_material_set_id)                
            op.set_id = set_id                     

def build_variations_layout(layout, obj):    
    col = layout.column(align=True)
    variation_list =[v for v in obj.mesh_lods.variations]                
    row = col.row()
    row.label(text="Variations")        
    if obj.override_library:        
        row.operator(OBJECT_OT_replace_with_object.bl_idname, text="", icon="EYEDROPPER") 
        row.operator(OBJECT_OT_flip_local_x_around_center.bl_idname, text="", icon="MOD_MIRROR") 
        col.template_icon_view(obj, "variations_enum")
    else:
        variation_list =[v for v in obj.mesh_lods.variations]                
        variation_list.append({"name": obj.name})
        variation_list.sort(key=lambda x: x['name'])   
                    
        for variation in variation_list:
            row = col.row(align=True)                        
            if hasattr(variation, "obj"):        
                row.context_pointer_set("new_variation", variation)                                                                                        
                #row.context_pointer_set("obj", obj)     
                op = row.operator(OBJECT_OT_activate_variation.bl_idname, text=variation.name ) #, icon_value=variation.obj.preview.icon_id if variation.obj.preview else None )            
                row.operator(OBJECT_OT_remove_variation.bl_idname, text="", icon="REMOVE")
            else:
                col.operator(DUMMY_OT_button.bl_idname, text=variation['name'], depress=True)                    
        col.operator(OBJECT_OT_add_variation.bl_idname, text="", icon="ADD")

############
# MESH LOD #
############
class OBJECT_OT_convert_to_lod_object(bpy.types.Operator):
    bl_idname = "mterrain.convert_to_lod_object"
    bl_label = "Convert object to lod"
    bl_options = {"REGISTER", "UNDO"}
    @classmethod
    def poll(self, context):
        return context.object and not context.object.override_library

    def execute(self, context):                
        for obj in context.selected_objects:
            lod = obj.mesh_lods.lods.add()                    
            obj.mesh_lods.lod_count += 1                        
            #self_variation = obj.mesh_lods.variations.add()
            #self_variation.name = obj.name
            #self_variation.obj = obj
            lod.mesh = obj.data.copy()            
            obj.data= lod.mesh
            if len(lod.mesh.materials)==0:
                lod.mesh.materials.append(None)
          # if len(lod.mesh.material_sets.surface_names) == 0:                
             #   s = obj.data.material_sets.surface_names.add()                
             #   s.value = "surface"
            if len(lod.mesh.material_sets.sets) == 0:                
                add_material_set(obj)
            if not "_lod_" in lod.mesh.name:
                lod.mesh.name = obj.name + "_lod_0"
                lod.lod = 0
            else:
                lod.lod = int(lod.mesh.name.split("_lod_")[1].split(".")[0])
                lod.mesh.name = obj.name + "_lod_" + str(lod.lod)
            set_count = len(lod.mesh.material_sets.sets)
            #materials = [mat for mat in lod.mesh.materials]                        
            validate_material_set_materials(lod.mesh, lod.mesh.material_sets.sets[0] )
            #material_count = len(lod.mesh.material_sets.sets[0].materials)
            #for i in range(max(1, len(lod.mesh.materials))):
            #    add_named_surface_to_mesh(lod.mesh)                     
            #    lod.mesh.material_sets.sets[0].materials[i].material = lod.mesh.materials[i]                
            with context.temp_override(object = obj):
                bpy.ops.mterrain.activate_mesh_lod(lod = lod.lod)
            obj.asset_mark()
            obj.asset_generate_preview()   
        return {'FINISHED'}

class OBJECT_OT_add_lod(bpy.types.Operator):
    bl_idname = "mterrain.add_mesh_lod"
    bl_label = "add mesh lod for object"
    bl_options = {"REGISTER", "UNDO"}
    @classmethod
    def poll(self, context):
        return context.object and not context.object.override_library and context.object.mesh_lods.lods_editable

    def execute(self, context):        
        all_lod = [m.lod for m in context.object.mesh_lods.lods]        
        lod = context.object.mesh_lods.lods.add()        
        lod.mesh = context.object.data.copy()
        lod.lod = max(all_lod) + 1                        
        
        #lod.mesh.use_fake_user = True
        lod.mesh.name = context.object.name + "_lod_" + str(lod.lod)
        context.object.mesh_lods.lod_count += 1
        for l in context.object.mesh_lods.lods:
            z = l
            print(l.lod)
        bpy.ops.mterrain.activate_mesh_lod(lod = lod.lod)        
        return {'FINISHED'}

class OBJECT_OT_remove_mesh_lod(bpy.types.Operator):
    bl_idname = "mterrain.remove_mesh_lod"
    bl_label = "remove mesh lod for object"    
    bl_options = {"REGISTER", "UNDO"}
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
    bl_idname = "mterrain.activate_mesh_lod"
    bl_label = "Activate mesh lod for object"    
    bl_options = {"REGISTER", "UNDO"}
    lod: bpy.props.IntProperty()
    @classmethod
    def poll(self, context):
        return True #not context.object.mesh_lods.active_lod == self.lod.obj

    def execute(self, context):
        if self.lod == context.object.mesh_lods.active_lod:
            self.report({"INFO"}, "Lod already active!")
            return{'CANCELLED'}
        set_active_lod(context.object, self.lod)        
        return {'FINISHED'}

class OBJECT_OT_Reset_Lod_Object(bpy.types.Operator):
    bl_idname = "mterrain.reset_lod_object"
    bl_label = "remove all mesh_lod data for object"  
    bl_options = {"REGISTER", "UNDO"}
    @classmethod
    def poll(self, context):
        return context.object and len(context.object.mesh_lods.lods) > 0

    def execute(self, context):
        for obj in context.selected_objects:
            obj.mesh_lods.variations.clear()
            obj.mesh_lods.lods.clear()
            obj.mesh_lods.active_lod = 0
            obj.mesh_lods.active_material_set_id = 0
            obj.mesh_lods.material_set_count = 0
            obj.mesh_lods.lod_count = 0
            obj.mesh_lods.lods_editable = True
            obj.mesh_lods.material_sets_editable = True          
        context.area.tag_redraw()  
        return {'FINISHED'}
#################
# Material Sets #
#################
class OBJECT_OT_AddNamedSurface(bpy.types.Operator):
    bl_idname = "mterrain.add_named_surface_to_mesh"
    bl_label = "Add named surface to mesh"
    bl_options = {"REGISTER", "UNDO"}
    @classmethod 
    def poll(self, context):
        return context.object and not context.object.override_library

    def execute(self, context):
        add_named_surface_to_object(context.object)
        return {'FINISHED'}

class OBJECT_OT_RemoveNamedSurface(bpy.types.Operator):
    bl_idname = "mterrain.remove_named_surface"
    bl_label = "Remove named surface for object"
    bl_options = {"REGISTER", "UNDO"}
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
    bl_idname = "mterrain.add_material_set"
    bl_label = "Add Material to Array"
    bl_options = {"REGISTER", "UNDO"}
    @classmethod 
    def poll(self, context):
        return context.object and len(context.object.data.material_sets.sets) < 126 and not context.object.override_library

    def execute(self, context):                
        add_material_set(context.object)
        return {'FINISHED'}

class OBJECT_OT_RemoveMaterialSet(bpy.types.Operator):
    bl_idname = "mterrain.remove_material_set"
    bl_label = "Remove Material set"
    bl_options = {"REGISTER", "UNDO"}
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
        m = lod.mesh.material_sets.sets.add()                
        m.material_set_id = lod.mesh.material_sets.next_material_set_id
        lod.mesh.material_sets.next_material_set_id += 1
        while len(lod.mesh.material_sets.sets[-1].materials) < len(lod.mesh.material_sets.surface_names):
            lod.mesh.material_sets.sets[-1].materials.add()

def remove_material_set(obj, set_id):
    for lod in obj.mesh_lods.lods:
        lod.mesh.material_sets.sets.remove(set_id)    
    obj.mesh_lods.material_set_count -= 1
        

class OBJECT_OT_ActivateMaterialSet(bpy.types.Operator):
    bl_idname = "mterrain.activate_material_set"
    bl_label = "Activate material set for object"
    bl_options = {"REGISTER", "UNDO"}
    set_id: bpy.props.IntProperty()
    @classmethod
    def poll(self, context):
        return context.object
    
    def execute(self, context):     
        if context.object.mesh_lods.active_material_set_id == self.set_id:
            self.report({"INFO"}, "Material set already active!")
        activate_material_set(context.object, self.set_id)
        return {'FINISHED'}    

class OBJECT_OT_Set_Face_Color(bpy.types.Operator):
    bl_idname = "mterrain.set_face_color"
    bl_label = "set face color"
    bl_options = {"REGISTER", "UNDO"}
    attribute_name: bpy.props.StringProperty(default="face_color")
    color: bpy.props.FloatVectorProperty(size=4, subtype="COLOR")
    @classmethod
    def description(self, context, properties):
        return context.color.name
    @classmethod
    def poll(self, context):
        return True#context.object and context.mode == "EDIT_MESH" and context.object.data.total_face_sel > 0
    
    def invoke(self, context, event):
        if event.ctrl or event.alt or event.shift:
            add_to_selection = event.shift
            remove_from_selection = event.alt
            select_face_by_color(attribute_name = self.attribute_name, target_color = self.color, add_to_selection=add_to_selection, remove_from_selection=remove_from_selection)
        else:
            set_face_color(attribute_name = self.attribute_name, target_color = self.color)
        return({"CANCELLED"})

def select_face_by_color(attribute_name = "face_color", target_color = (0.99,0.0, 0.0, 1.0), add_to_selection=False, remove_from_selection=False):    
    obj = bpy.context.object    
    if obj.type == 'MESH':        
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        # Ensure a color attribute exists
        color_layer = bm.loops.layers.color.get(attribute_name)
        if not color_layer:
            return                            

        for face_index, face in enumerate(bm.faces):                
            for loop in face.loops:
                e = 0.005
                if abs(loop[color_layer][0] - target_color[0]) < e and abs(loop[color_layer][1] - target_color[1]) < e and abs(loop[color_layer][2] - target_color[2]) < e and abs(loop[color_layer][3] - target_color[3]) < e:     
                    if not remove_from_selection:
                        face.select = True
                    else:
                        face.select = False
                        
                else:
                    if not add_to_selection and not remove_from_selection:
                        face.select = False

        # Update the bmesh and exit edit mode
        bmesh.update_edit_mesh(obj.data)


def set_face_color(attribute_name = "face_color", target_color = (0.99,0.0, 0.0, 1.0)):
    # Get the active object (make sure it's a mesh)
    obj = bpy.context.object

    # Ensure we're working with a mesh
    if obj.type == 'MESH':
        # Enter edit mode and get the bmesh representation
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)

        # Ensure a color attribute exists or create one
        color_layer = bm.loops.layers.color.get(attribute_name)
        if not color_layer:
            color_layer = bm.loops.layers.color.new(attribute_name)

        # Iterate over the faces to set color
        target_face_index = 0  # Replace with the desired face index
        

        for face_index, face in enumerate(bm.faces):
            if face.select:
    #        if face_index == target_face_index:
                for loop in face.loops:
                    loop[color_layer] = target_color                

        # Update the bmesh and exit edit mode
        bmesh.update_edit_mesh(obj.data)

class OBJECT_OT_add_color_to_palette(bpy.types.Operator):
    bl_idname = "mterrain.add_color_to_palette"
    bl_label = "add_color_to_palette"
    bl_options = {"REGISTER", "UNDO"}
    color: bpy.props.FloatVectorProperty(size=4, subtype="COLOR", default=(0.,0.,0.,1.))
    new_name: bpy.props.StringProperty(default="new_color")
    
    def execute(self, context):             
        color = context.scene.color_palette.colors.add()
        color.color = self.color        
        color.name = self.new_name
        color.icon_name = str(len(context.scene.color_palette.colors))
        return {'FINISHED'}            

class OBJECT_OT_Make_Palette_Material(bpy.types.Operator):
    bl_idname = "mterrain.make_palette_material"
    bl_label = "make_palette_material"
    bl_options = {"REGISTER", "UNDO"}    
    
    def execute(self, context):                     
        if not "color_palette" in bpy.data.materials:
            mat = bpy.data.materials.new("color_palette")
            mat.use_nodes = True
            tree = mat.node_tree    
            color_attribute = tree.nodes.new("ShaderNodeVertexColor")
            color_attribute.layer_name = "face_color"
            tree.links.new(color_attribute.outputs[0], tree.nodes['Principled BSDF'].inputs[0])
        mat = bpy.data.materials['color_palette']
        context.object.data.materials.clear()
        mat = context.object.data.materials.append(mat)
                
        if not "face_color" in context.object.data.color_attributes:            
            context.object.data.color_attributes.new("face_color", "BYTE_COLOR", "CORNER")

        return {'FINISHED'}    

class OBJECT_OT_update_color_in_palette(bpy.types.Operator):
    bl_idname = "mterrain.update_color_in_palette"
    bl_label = "update_color_in_palette"
    bl_options = {"REGISTER", "UNDO"}
    index: bpy.props.IntProperty()
    new_name: bpy.props.StringProperty()
    new_color: bpy.props.FloatVectorProperty(size=4, subtype="COLOR")
    def execute(self, context):     
        context.scene['color_palette'][index] = self.new_color
        context.scene['color_palette'][name] = self.new_name
        return {'FINISHED'}            

class OBJECT_OT_bake_surface_id_to_vertex_color_r(bpy.types.Operator):
    bl_idname = "mterrain.bake_surface_id_to_vertex_color_r"
    bl_label = "bake_surface_id_to_vertex_color_r"
    bl_options = {"REGISTER", "UNDO"}    
    attribute_name: bpy.props.StringProperty(default="SurfaceID")
    @classmethod
    def poll(self, context):
        return context.object and context.mode == "EDIT"
    
    def execute(self, context):     
        bake_surface_id_to_vertex_color_r(color_attribute_name = self.attribute_name)
        return {'FINISHED'}            

def bake_surface_id_to_vertex_color_r(color_attribute_name = "SurfaceID"):
    # Settings    
    max_surfaces = 64  # Maximum surface IDs

    # Get the active object
    obj = bpy.context.object

    # Ensure the object is a mesh
    if obj.type != 'MESH':
        raise ValueError("Active object must be a mesh")

    # Access or create the color attribute
    color_attribute = obj.data.color_attributes.get(color_attribute_name)
    if not color_attribute:
        color_attribute = obj.data.color_attributes.new(name=color_attribute_name, type='FLOAT_COLOR', domain='CORNER')

    # Iterate over faces and set the red channel for each corner
    for poly in obj.data.polygons:
        for loop_idx in poly.loop_indices:
            surface_id = poly.material_index / (max_surfaces - 1) if poly.material_index!=0 or max_surfaces ==1 else 0
            obj.data.color_attributes[color_attribute_name].data[loop_idx].color = (surface_id, 0.0,0.0,1.0)



##############
# VARIATIONS #
##############  
class OBJECT_OT_replace_with_object(bpy.types.Operator):
    bl_idname = "mterrain.replace_object"
    bl_label = "replace object with another object"
    bl_options = {"REGISTER", "UNDO"}    
    @classmethod
    def poll(self, context):
        return context.object and len(context.object.mesh_lods.lods)>0 and context.object.override_library

    def modal(self, context, event):    
        if event.type =='MOUSEMOVE':
            area = get_area_under_mouse(context.screen, event.mouse_x, event.mouse_y)
            if area.type == "VIEW_3D":                
                result, location, normal, index, obj, matrix = raypick(context,event)
                if result and obj:                                
                    context.workspace.status_text_set(f"Hovering over: {obj.name} (Click to select)")
                else:            
                    context.workspace.status_text_set("Click on object to replace")

        elif event.type == 'LEFTMOUSE' and event.value=='RELEASE':                                    
            area = get_area_under_mouse(context.screen, event.mouse_x, event.mouse_y)
            if area.type == "VIEW_3D":                
                result, location, normal, index, obj, matrix = raypick(context,event)
                if result and obj:
                    replace_object_with_object(context, context.object, obj)            
            return {'FINISHED'}    
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):                
        context.window.cursor_set('EYEDROPPER')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}        

class OBJECT_OT_flip_local_x_around_center(bpy.types.Operator):
    bl_idname = "mterrain.flip_local_x_around_center"
    bl_label = "flip object around it's local x axis, translate back into original position"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type== "MESH"
    
    def execute(self, context):          
        obj = context.object           
        # Get the object's local bounding box center
        local_center = sum((mathutils.Vector(corner) for corner in obj.bound_box), mathutils.Vector()) / 8.0
        # Convert local center to global coordinates
        global_center = obj.matrix_world @ local_center
        # Create a transformation matrix to translate to center, scale, and translate back
        scale_factor = -1  # Adjust as needed
        scale_matrix = mathutils.Matrix.Scale(scale_factor, 4, obj.matrix_world.to_3x3().col[0])  # Scale along local X-axis        
        # Translate to origin, apply scale, translate back
        translation_to_center = mathutils.Matrix.Translation(-global_center)
        translation_back = mathutils.Matrix.Translation(global_center)
        transformation_matrix = translation_back @ scale_matrix @ translation_to_center

        # Apply the transformation to the object
        obj.matrix_world = transformation_matrix @ obj.matrix_world
        return {'FINISHED'}    

def consolidate_variations(new_variations_list):    
    for variation_to_update in new_variations_list:                    
        for new_variation in new_variations_list:
            variations = variation_to_update['obj'].mesh_lods.variations
            if new_variation['name'] in variations or new_variation['name'] == variation_to_update['obj'].name:                 
                continue
            variation = variations.add()
            variation.name = new_variation['name']
            variation.obj = new_variation['obj']

class OBJECT_OT_merge_variations(bpy.types.Operator):
    bl_idname = "mterrain.merge_variations"
    bl_label = "merge_variations for selected objects"    
    bl_options = {"REGISTER", "UNDO"}
    @classmethod
    def poll(self, context):
        return context.selected_objects and len(context.selected_objects) > 1

    def execute(self, context):
        new_variations_list = []
        for obj in context.selected_objects:
            for variation in obj.mesh_lods.variations:
                if not variation.name in new_variations_list:
                    new_variations_list.append(variation)
            if not obj in [variation['obj'] for variation in new_variations_list]:
                new_variations_list.append({"obj":obj, "name":obj.name})        
        consolidate_variations(new_variations_list)
        return {'FINISHED'}


def raypick(context, event):
    # Perform ray cast to find the object under the mouse
    region = context.region
    rv3d = context.space_data.region_3d
    coord = (event.mouse_region_x, event.mouse_region_y)
    
    view_vector = bpy_extras.view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = bpy_extras.view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        
    result, location, normal, index, obj, matrix = context.scene.ray_cast(context.view_layer.depsgraph, ray_origin, view_vector)  
    return result, location, normal, index, obj, matrix

def get_area_under_mouse(screen, mouse_x, mouse_y):
        """Returns the area under the mouse cursor."""
        for area in screen.areas:
            if area.x <= mouse_x <= area.x + area.width and \
            area.y <= mouse_y <= area.y + area.height:
                return area
        return None

class OBJECT_OT_add_variation(bpy.types.Operator):
    bl_idname = "mterrain.add_variation"
    bl_label = "Add variation for object"    
    bl_options = {"REGISTER", "UNDO"}
        
    def modal(self, context, event):
        obj = None
        if event.type == 'LEFTMOUSE' and event.value=='RELEASE':                                    
            area = get_area_under_mouse(context.screen, event.mouse_x, event.mouse_y)
            if area.type == "VIEW_3D":                
                result, location, normal, index, obj, matrix = raypick(context,event)
            elif area.type =="OUTLINER":
                pass
                #with context.temp_override(area=area, region=area.regions[1]):
                #    bpy.ops.outliner.item_activate(mouse_x=event.mouse_region_x, mouse_y=event.mouse_region_y,deselect_all=True)
                #print("\n\n\nAAA")
                #context.object
            else:                
                return{'CANCELLED'}
            if obj:                                                
                new_variations_list = []                
                for new_variation in obj.mesh_lods.variations:
                    if new_variation.name in context.object.mesh_lods.variations:                
                        self.report({'INFO'}, "Can't add variation: Object is already a variation")
                        return {"CANCELLED"}
                    if not new_variation in new_variations_list: 
                        new_variations_list.append(new_variation)
                for old_variation in context.object.mesh_lods.variations:
                    if not old_variation in new_variations_list:
                        new_variations_list.append(old_variation)                                        
                if not obj in [variation.obj for variation in new_variations_list]:
                    new_variations_list.append({"obj":obj, "name":obj.name})
                if not context.object in [variation['obj'] for variation in new_variations_list]:
                    new_variations_list.append({"obj":context.object, "name":context.object.name})    
                consolidate_variations(new_variations_list)                                
            context.window.cursor_set('DEFAULT')
            context.area.tag_redraw()
            return {'FINISHED'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):          
        #Fix fake variation created when duplicating object
        if len(context.object.mesh_lods.variations) >0 and not context.object in [v.obj for v in context.object.mesh_lods.variations[0].obj.mesh_lods.variations]:      
            context.object.mesh_lods.variations.clear()
        context.window.cursor_set('EYEDROPPER')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}        

class OBJECT_OT_remove_variation(bpy.types.Operator):
    bl_idname = "mterrain.remove_variation"
    bl_label = "remove variation for object"    
    bl_options = {"REGISTER", "UNDO"}
    @classmethod
    def poll(self, context):
        return context.object and len(context.object.mesh_lods.variations) > 0 and hasattr(context, "new_variation") and context.new_variation != None and hasattr(context.new_variation, "obj")

    def execute(self, context):
        obj_to_remove = context.new_variation.obj
        for obj in [variation.obj for variation in obj_to_remove.mesh_lods.variations]:
            obj.mesh_lods.variations.remove(obj.mesh_lods.variations.find(context.new_variation.name))                        
        obj_to_remove.mesh_lods.variations.clear()
        context.region.tag_redraw()
        
        return {'FINISHED'}

def update_variation(self, context):
    if context.object.variations_enum == context.object.name: return
    variation = [v for v in context.object.mesh_lods.variations if v.name == context.object.variations_enum][0]
    with context.temp_override(new_variation=variation):
        bpy.ops.mterrain.activate_variation()

class OBJECT_OT_activate_variation(bpy.types.Operator):
    bl_idname = "mterrain.activate_variation"
    bl_label = "Activate variation for object"    
    bl_options = {"REGISTER", "UNDO"}
    material_set_id: bpy.props.IntProperty(default=0, min=0)
    
    @classmethod
    def poll(self, context):
        if not context.object: return False
        if not len(context.object.mesh_lods.variations) > 0: return False
        if not hasattr(context, "new_variation"): return False                
        if context.new_variation == None: return False
        #if context.new_variation.obj == context.obj: return False
        return True

    def execute(self, context):       
        if not hasattr(context.new_variation, "obj") or context.new_variation.obj == context.object: 
            self.report({'INFO'}, "Variation already active!")
            return {'CANCELLED'}
        obj = context.object
        if obj.library:
            original_obj.override_create()    
        if not obj.override_library:     
            for o in context.selected_objects:
                o.select_set(False)
            new_obj = context.new_variation.obj
            if not new_obj.name in context.view_layer.objects:
                context.scene.collection.objects.link(new_obj)
            new_obj.select_set(True)
            bpy.context.view_layer.objects.active = new_obj
            activate_material_set(new_obj, self.material_set_id)        
        else:
            context.new_variation.obj = replace_object_with_object(context, context.object, context.new_variation.obj)
        return {'FINISHED'}
        
def replace_object_with_object(context, original_obj, template_obj):
    if original_obj.library:
        original_obj.override_create()        
    
    if not template_obj.override_library:
        template_obj = template_obj.override_create()            
    new_obj = template_obj.copy()
    if not new_obj.override_library:
        for obj in context.selected_objects:                
            obj.select_set(False)                                    
        activate_material_set(new_obj, min(self.material_set_id, len(new_obj.mesh_lods.lods[0].mesh.material_sets.sets)-1))
                
    if new_obj.is_property_readonly("location"):            
        new_obj = new_obj.override_create()            
        for lod in new_obj.mesh_lods.lods:
            lod.mesh = lod.mesh.override_create()                                        
        set_active_lod(new_obj, 0)            

    new_obj.location = original_obj.location
    new_obj.scale = original_obj.scale
    new_obj.rotation_euler = original_obj.rotation_euler                                                
    
    for col in original_obj.users_collection:
        col.objects.link(new_obj)                
        col.objects.unlink(original_obj)
    new_obj.select_set(True)
    bpy.context.view_layer.objects.active = new_obj
    return new_obj

class DUMMY_OT_button(bpy.types.Operator):
    bl_idname = "mterrain.dummy_button"
    bl_label = "Dummy Button"
    
    def execute(self, context):        
        return {'FINISHED'}

def get_variations_enum(self, context):
    obj = context.object
    variation_list =[v for v in obj.mesh_lods.variations]                    
    if obj.override_library:
        variation_list.append({"name": obj.override_library.reference.name, "obj": obj})    
    else:
        variation_list.append({"name": obj.name, "obj": obj})
    variation_list.sort(key=lambda x: x['name'])          
    result = []
    passed_current_id = False
    for i, variation in enumerate(variation_list):
        variation['obj'].preview_ensure()
        if variation['obj'] == obj:
            result.append((str(-1),variation['obj'].name,variation['obj'].name, variation['obj'].preview.icon_id, i))
            passed_current_id = True
        else:
            variation_id = i if not passed_current_id else i-1
            result.append((variation['obj'].name,variation['obj'].name,variation['obj'].name, variation['obj'].preview.icon_id, i))
    return result 

def depsgraph_update_post(scene):        
    old_object_names = scene.scene_objects.split(",")    
    object_names = [obj.name for obj in scene.objects if obj.name in bpy.data.objects]
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
def menu_func_export(self, context):
    self.layout.operator(MTerrain_OT_ExportAsGLB.bl_idname, text="Export MTerrain Assets (.glb)")

addon_keymaps= []
def register():
    classes = [        
        VariationObject,         
        MeshLod,
        MeshLods,
        ColorPaletteItem,
        ColorPalette,
        
        
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
        MTerrain_OT_Fix_Collection_Offsets, 
        MTerrain_PT_Tool,        
        
        OBJECT_OT_AddNamedSurface,
        OBJECT_OT_RemoveNamedSurface,
        OBJECT_OT_AddMaterialSet,
        OBJECT_OT_RemoveMaterialSet,
        OBJECT_OT_ActivateMaterialSet,

        OBJECT_OT_merge_variations,
        OBJECT_OT_add_variation,
        OBJECT_OT_remove_variation,
        OBJECT_OT_activate_variation,
        DUMMY_OT_button,

        MTerrain_AST_Asset_Picker,      
        OBJECT_OT_drag_drop_asset,
        
        MTerrain_OT_prepare_tilemap_for_painting,
        MTerrain_OT_convert_tilemap_to_instances,        
        OBJECT_OT_Reset_Lod_Object,

        OBJECT_OT_flip_local_x_around_center,
        OBJECT_OT_replace_with_object,

        OBJECT_OT_Set_Face_Color, 
        OBJECT_OT_add_color_to_palette, 
        OBJECT_OT_update_color_in_palette, 
        OBJECT_OT_bake_surface_id_to_vertex_color_r,
        OBJECT_OT_Make_Palette_Material
    ]                
    for c in classes:
        bpy.utils.register_class(c)    
    
    bpy.types.WorkSpace.selected_asset = bpy.props.IntProperty(
        name="selected_asset", default=0         
    )       
    bpy.types.Scene.scene_objects = bpy.props.StringProperty()            
    bpy.types.Mesh.material_sets = bpy.props.PointerProperty(type=MaterialSets) 
    bpy.types.Object.mesh_lods = bpy.props.PointerProperty(type=MeshLods)             
    bpy.types.Object.variations_enum = bpy.props.EnumProperty(items=get_variations_enum, override={"LIBRARY_OVERRIDABLE"}, update=update_variation)    
    bpy.types.Scene.color_palette = bpy.props.PointerProperty(type=ColorPalette)
    props = [bpy.types.WorkSpace.selected_asset, 
        bpy.types.Mesh.material_sets, 
        bpy.types.Scene.scene_objects, 
        bpy.types.Object.variations_enum, 
        bpy.types.Scene.color_palette
    ]
    #bpy.types.ASSETSHELF_PT_display.append(MTerrain_PT_Tool.draw)
    #bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_post)
    
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    # Asset Shelf
    km = bpy.context.window_manager.keyconfigs.addon.keymaps.new(name="Asset Shelf")
    # Drag to blend pose.
    kmi = km.keymap_items.new("mterrain.drag_drop_asset", "LEFTMOUSE", "CLICK_DRAG")    
    addon_keymaps.append(km)

def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    for c in classes:
        bpy.utils.unregister_class(c)    

    for prop in props:
        del prop
    #bpy.types.ASSETSHELF_PT_display.remove(MTerrain_PT_Tool.draw)
    #bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_post)    

    bpy.context.window_manager.keyconfigs.addon.keymaps.remove(addon_keymaps[0])    

if __name__ == "__main__":
    register()

#TODO:
# - changes to material slots should update UI
# - 