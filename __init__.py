
bl_info = {
    "name": "MTerrain Helper",    
    "category": "Object",
}

import bpy
import os
from bpy_extras.io_utils import ExportHelper
## OPERATOR ###

class MTerrain_OT_ExportAsGLB(bpy.types.Operator, ExportHelper):
    """Export selected objects as scene, updating blend_path custom property"""
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
        material_to_delete = []
        objects_to_delete = []
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
                new_obj.select_set(True)
                new_obj['blend_file'] = obj.override_library.reference.library.name
                new_obj['active_material_set'] = obj.mesh_lods.active_material_set
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
                                material_array.append(material.material.name)
                            material_sets.append(material_array)
                        new_object['material_sets'] = material_sets                                                
            
            ###########################
            # Add Tags to collections #
            ###########################
            for col in obj.users_collection:
                if col.asset_data and obj.name in col.objects:
                    obj['tags'] = [tag.name for tag in col.asset_data.tags]                 
                    break
        

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
                activate_material_set(obj, obj.mesh_lods.active_material_set)
                            
        return {'FINISHED'}

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
        layout.label(text="AHHHH")

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
        #layout.operator(MTerrain_OT_Toggle_Lods_Hidden.bl_idname, text="Toggle hide LODs")        
        layout.operator(MTerrain_OT_Fix_Collection_Offsets.bl_idname, text="fix collection offset")
        layout.operator(MTerrain_OT_ExportAsGLB.bl_idname, text='Export')          
        
        if not context.selected_objects or len(context.selected_objects) == 0: return        
        layout.operator(MTerrain_OT_Convert_Selected_Objects_To_Assets.bl_idname, text="Convert selected to asset collections")
        obj = context.object

        if len(obj.mesh_lods.lods) == 0:
            layout.operator(OBJECT_OT_convert_to_lod_object.bl_idname, text="Convert to Lod object")
        else:              
            col = layout.column(align=True)
            row = col.row()
            row.alignment = 'CENTER'        
            row.label(text="Mesh Lods")                       
            lods = [lod for lod in obj.mesh_lods.lods]         
            lods.sort(key=lambda x: x.lod)        
            
            for mesh_lod in lods:                        
                icon = "CHECKBOX_DEHLT" if mesh_lod.lod != obj.mesh_lods.active_lod else "CHECKBOX_HLT"
                row = col.row(align=True)
                split = row.split(factor=0.7, align=True)
                split.operator(OBJECT_OT_activate_lod.bl_idname, text="Lod " + str(mesh_lod.lod), icon=icon).lod = mesh_lod.lod                        
                split.prop(mesh_lod, "lod", text="")
                row.context_pointer_set("lod_dictionary", mesh_lod)
                if len(lods) >1:
                    op = row.operator(OBJECT_OT_remove_mesh_lod.bl_idname, icon="REMOVE", text="")                                
                                                
            col.operator(OBJECT_OT_add_lod.bl_idname, icon="ADD", text="")  
            row = layout.row()
            row.alignment = 'CENTER'        
            row.label(text="Lod From Object")      
            layout.prop(obj.mesh_lods, "object_for_replacing_lod_mesh", text="", )

            row = layout.row()
            row.alignment = 'CENTER'        
            row.label(text="Surface Names")                
            col = layout.column(align=True)
            for i, surface_name in enumerate(obj.data.material_sets.surface_names):
                row = col.row()
                row.prop(surface_name, "value", text="") #str(i))                
                row.operator(OBJECT_OT_RemoveNamedSurface.bl_idname, icon="REMOVE", text="").surface_id = i
            layout.operator(OBJECT_OT_AddNamedSurface.bl_idname, icon="ADD", text="")
            layout.separator()
                    
            row = layout.row()
            row.alignment = 'CENTER'
            row.label(text="Material Sets")
            
            for set_id, material_set in enumerate(obj.data.material_sets.sets):
                #header, panel = layout.panel("material_set_" + str(i))
                row = layout.row()
                icon = "CHECKBOX_DEHLT" if set_id != obj.mesh_lods.active_material_set else "CHECKBOX_HLT"
                row.operator(OBJECT_OT_ActivateMaterialSet.bl_idname, text="set " + str(set_id), icon=icon).set_id = set_id
                if len(obj.data.material_sets.sets)>1:
                    row.operator(OBJECT_OT_RemoveMaterialSet.bl_idname, icon="REMOVE", text="").set_id = set_id
                col = layout.column(align=True)                        
                for surface_id, materials in enumerate(material_set.materials):  
                    if surface_id > len(obj.data.material_sets.surface_names): break                   
                    row = col.row()
                    row.prop(materials, "material", text= obj.data.material_sets.surface_names[surface_id].value)
                    
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
class StringItem(bpy.types.PropertyGroup):
    value: bpy.props.StringProperty(name="Value")

class MaterialItem(bpy.types.PropertyGroup):
    material: bpy.props.PointerProperty(type=bpy.types.Material)

class MaterialSet(bpy.types.PropertyGroup):
    materials: bpy.props.CollectionProperty(type=MaterialItem)

class MaterialSets(bpy.types.PropertyGroup):
    surface_names: bpy.props.CollectionProperty(type=StringItem)    
    sets: bpy.props.CollectionProperty(type=MaterialSet)    
    collapsed_panels: bpy.props.BoolVectorProperty()

class OBJECT_OT_AddNamedSurface(bpy.types.Operator):
    bl_idname = "object.add_named_surface_to_mesh"
    bl_label = "Add named surface to mesh"
    @classmethod 
    def poll(self, context):
        return context.object and not context.object.override_library

    def execute(self, context):
        add_named_surface_to_object(context.object)
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
    mesh.material_sets.surface_names[-1].value = "Material"    
    surface_count = len(mesh.material_sets.surface_names)
    for material_set in mesh.material_sets.sets:
        for i in range(abs(len(material_set.materials) - surface_count)):            
            if len(material_set.materials) < surface_count:            
                material_set.materials.add()
            else:
                material_set.materials.remove(material_set.materials[-1])
        

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

def remove_named_surface(mesh, surface_id):
    if surface_id == -1:
        surface_id = len(mesh.material_sets.surface_names)-1
    mesh.material_sets.surface_names.remove(surface_id)    
    for material_set in mesh.material_sets.sets:
        material_set.materials.remove(surface_id)
        

class OBJECT_OT_AddMaterialSet(bpy.types.Operator):
    bl_idname = "object.add_material_set"
    bl_label = "Add Material to Array"
    @classmethod 
    def poll(self, context):
        return context.object and len(context.object.data.material_sets.sets) < 126 and not context.object.override_library

    def execute(self, context):        
        for lod in context.object.mesh_lods.lods:                    
            add_material_set(lod.mesh)
        return {'FINISHED'}

def add_material_set(mesh):    
    mesh.material_sets.sets.add()
    while len(mesh.material_sets.sets[-1].materials) < len(mesh.material_sets.surface_names):
        mesh.material_sets.sets[-1].materials.add()


class OBJECT_OT_RemoveMaterialSet(bpy.types.Operator):
    bl_idname = "object.remove_material_set"
    bl_label = "Remove Material set"

    set_id: bpy.props.IntProperty()
    @classmethod
    def poll(self, context):
        return context.object and not context.object.override_library

    def execute(self, context):
        obj = context.object
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}
        remove_material_set(obj, self.set_id)
        return {'FINISHED'}

def remove_material_set(obj, set_id):
    for lod in obj.mesh_lods.lods:
        lod.mesh.material_sets.sets.remove(set_id)    
        

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

def activate_material_set(obj, set_id):            
    if len(obj.data.material_sets.sets) < set_id:
        return
    for i in range( abs(len(obj.material_slots) - len(obj.data.material_sets.sets[set_id].materials)) ):    
        if len(obj.material_slots) < len(obj.data.material_sets.sets[set_id].materials):
            obj.data.materials.append(None)
        else:
            add_named_surface_to_mesh(obj.data)

    obj.mesh_lods.active_material_set = set_id
    for i, slot in enumerate(obj.material_slots):
        if not slot.is_property_readonly("material"):            
            slot.material = obj.data.material_sets.sets[set_id].materials[i].material
            


############
# MESH LOD #
############
class MeshLod(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(type=bpy.types.Mesh)    
    def on_update_lod(self, context):              
        if self.lod == self.old_lod:             
            return        
        all_lod = []        
        lod_ok = True
        for m in context.object.mesh_lods.lods:
            if m == self: continue            
            all_lod.append(m.lod)
            if m.lod == self.lod:                
                lod_ok = False
        if lod_ok == False:
            new_lod = self.lod                            
            i = 0
            up = new_lod < self.old_lod            
            while new_lod in all_lod:                
                i+=1
                if up:
                    if new_lod - i < 0:
                        i = 0
                        up = False
                        continue
                    if not new_lod - i in all_lod:
                        new_lod = new_lod - i
                        break              
                else:             
                    if not new_lod + i in all_lod:
                        new_lod = new_lod + i
                        break            
            self.lod = new_lod                            
        set_active_lod(context.object, self.lod)                        
        if self.mesh:
            self.mesh.name = self.mesh.name.split("_lod_")[0] + "_lod_" + str(self.lod)                        
    
    def get_lod(self):            
        return self['lod']
    def set_lod(self, value):                    
        if 'lod' in self:
            self['old_lod'] = self['lod']
        self['lod'] = value        

    lod: bpy.props.IntProperty(default=0, min=0, soft_max=20, get=get_lod, update=on_update_lod, set=set_lod)    
    old_lod: bpy.props.IntProperty(default=0)
    # def get_availabled_lod_options(self, context):        
    #     unavailable_lods = []
    #     for lod in context.object.mesh_lods.lods:           
    #         if lod != self:
    #             unavailable_lods.append(lod.lod)      
    #         else:
    #             print(lod.lod)
    #     items = []        
    #     for i in range(3):
    #         if not i in unavailable_lods:            
    #             items.append((str(i), str(i), ""))
    #         else:
    #             print(i)
    #             print(unavailable_lods)
    #     return items

    #lod: bpy.props.EnumProperty(name="lod", items=get_availabled_lod_options)
    #material_sets: bpy.props.IntVectorProperty() #array of material_set ids
    
class MeshLods(bpy.types.PropertyGroup):
    lods: bpy.props.CollectionProperty(type=MeshLod)        
    active_lod: bpy.props.IntProperty(default=0, name="active_lod", override={"LIBRARY_OVERRIDABLE"})    
    active_material_set: bpy.props.IntProperty(default=0, override={"LIBRARY_OVERRIDABLE"})
    def replace_lod_mesh(self, context):
        if self.object_for_replacing_lod_mesh == None: return        
        target_lod = [lod for lod in self.lods if lod.lod == self.active_lod][0]        
        target_lod.mesh = self.object_for_replacing_lod_mesh.data        
        
        if len(target_lod.mesh.material_sets.sets)<1:            
            add_material_set(target_lod.mesh)
        if len(target_lod.mesh.material_sets.surface_names) == 0:
            add_named_surface_to_mesh(target_lod.mesh)        
        self.object_for_replacing_lod_mesh = None
        set_active_lod(context.object, self.active_lod)
    object_for_replacing_lod_mesh: bpy.props.PointerProperty(type=bpy.types.Object, update=replace_lod_mesh, description="Choose a mesh object to copy it's mesh into the current Lod")

class OBJECT_OT_convert_to_lod_object(bpy.types.Operator):
    bl_idname = "object.convert_to_lod_object"
    bl_label = "Convert object to lod"
    @classmethod
    def poll(self, context):
        return context.object and not context.object.override_library

    def execute(self, context):                
        for obj in context.selected_objects:
            lod = obj.mesh_lods.lods.add()        
            lod.mesh = obj.data.copy()
            lod.mesh.use_fake_user = True
            if not "_lod_" in lod.mesh.name:
                lod.mesh.name = obj.name + "_lod_0"
                lod.lod = 0
            else:
                lod.lod = int(lod.mesh.name.split("_lod_")[1])
                lod.mesh.name = obj.name + "_lod_" + str(lod.lod)
            materials = [mat.name for mat in lod.mesh.materials]            
                        
            for i in range(max(1, len(lod.mesh.materials))):
                add_named_surface_to_mesh(lod.mesh)
            add_material_set(lod.mesh)    
            for i, material in enumerate(lod.mesh.material_sets.sets[0].materials):
                material.material = lod.mesh.materials[i]
            with context.temp_override(object = obj):
                bpy.ops.object.activate_mesh_lod(lod = lod.lod)
                
        return {'FINISHED'}

class OBJECT_OT_add_lod(bpy.types.Operator):
    bl_idname = "object.add_mesh_lod"
    bl_label = "add mesh lod for object"

    @classmethod
    def poll(self, context):
        return context.object and not context.object.override_library

    def execute(self, context):        
        all_lod = [m.lod for m in context.object.mesh_lods.lods]        
        lod = context.object.mesh_lods.lods.add()        
        lod.lod = max(all_lod) + 1                        
        lod.mesh = context.object.data.copy()
        lod.mesh.use_fake_user = True
        lod.mesh.name = context.object.name + "_lod_" + str(lod.lod)
        bpy.ops.object.activate_mesh_lod(lod = lod.lod)        
        return {'FINISHED'}

class OBJECT_OT_remove_mesh_lod(bpy.types.Operator):
    bl_idname = "object.remove_mesh_lod"
    bl_label = "remove mesh lod for object"    
    
    @classmethod
    def poll(self, context):
        return context.object and not context.object.override_library
  
    def execute(self, context):              
        lod = context.lod_dictionary.lod   
        if not context.object.type == 'MESH': return {'CANCELLED'}        
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

def set_active_lod(obj, lod):    
    if not obj.type == 'MESH': return        
    new_obj = confirm_or_make_overrides(obj,lod)
    mesh = [x for x in new_obj.mesh_lods.lods if x.lod == lod][0].mesh
    new_obj.data = mesh
    new_obj.mesh_lods.active_lod = lod
    activate_material_set(obj, obj.mesh_lods.active_material_set)
    
def confirm_or_make_overrides(obj,new_lod):    
    if not obj.override_library and not obj.library:         
        return obj
    new_obj = obj
    if not obj.override_library:        
        new_obj = obj.override_create()
        for col in obj.users_collection:
            col.objects.unlink(obj)
            col.objects.link(new_obj)        
    if not new_obj.data.override_library:        
        lod_to_update = [lod for lod in new_obj.mesh_lods.lods if lod.lod == new_lod ][0]        
        new_mesh = new_obj.data.override_create()        
        lod_to_update.mesh = new_mesh
        new_obj.data = new_mesh            
    return new_obj
    #     for prop in obj.data.override_library.properties:
    #         if prop.rna_path == override_rna_path:
    #             return
    # new_prop = obj.data.override_library.properties.add(override_rna_path)
    # new_prop.operations.add("REPLACE")
    

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
        MTerrain_AST_Asset_Picker,      
        OBJECT_OT_AddNamedSurface,
        OBJECT_OT_RemoveNamedSurface,
        OBJECT_OT_AddMaterialSet,
        OBJECT_OT_RemoveMaterialSet,
        OBJECT_OT_ActivateMaterialSet
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
