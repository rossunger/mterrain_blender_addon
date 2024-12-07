import bpy
import bpy_extras
import bmesh

class ColorPaletteItem(bpy.types.PropertyGroup):
    def update_color(self,context):
        if not hasattr(context.scene.color_palette, "previews"):
            context.scene.color_palette.previews = bpy.utils.previews.new()
        previews = context.scene.color_palette.previews
        if not self.icon_name in previews:                    
            icon = previews.load(self.icon_name, "", 'IMAGE')
            icon.icon_size = (32,32)
            icon.image_size = (32,32)
        else:
            icon = previews[self.icon_name]        
        icon.icon_pixels_float = [self.color[0], self.color[1], self.color[2], self.color[3], ] * (32*32)
        icon.image_pixels_float = [self.color[0], self.color[1], self.color[2], self.color[3], ] * (32*32)
        self.icon_id = icon.icon_id
        
        # UPDATE faces that had the old color        
        e = 0.075
        original_mode = context.object.mode
        bpy.ops.object.mode_set(mode="OBJECT")        
        for obj in bpy.data.objects:            
            if obj.type !="MESH": continue     
            if not "face_color" in obj.data.color_attributes: continue
            for i, loop in enumerate(obj.data.color_attributes['face_color'].data):                                        
                if abs(loop.color[0] - self.old_color[0]) < e and abs(loop.color[1] - self.old_color[1]) < e and abs(loop.color[2] - self.old_color[2]) < e and abs(loop.color[3] - self.old_color[3]) < e:                                                         
                    loop.color[0] = self.color[0]                    
                    loop.color[1] = self.color[1]                    
                    loop.color[2] = self.color[2]                    
                    loop.color[3] = self.color[3]                    
        bpy.ops.object.mode_set(mode=original_mode)                
        self.old_color[0] = self.color[0]
        self.old_color[1] = self.color[1]
        self.old_color[2] = self.color[2]
        self.old_color[3] = self.color[3]

    color: bpy.props.FloatVectorProperty(size=4, subtype="COLOR", default=(0.,0.,0.,1.), min=0.0, max=1.0, update=update_color)        
    old_color: bpy.props.FloatVectorProperty(size=4, subtype="COLOR", default=(0.,0.,0.,1.), min=0.0, max=1.0)        
    icon_id: bpy.props.IntProperty()
    icon_name: bpy.props.StringProperty()

class ColorPalette(bpy.types.PropertyGroup):
    colors: bpy.props.CollectionProperty(type=ColorPaletteItem)
    edit_locked: bpy.props.BoolProperty(default=True)    
    previews = bpy.utils.previews.new()
class StringItem(bpy.types.PropertyGroup):
    value: bpy.props.StringProperty(name="Value")

class MaterialItem(bpy.types.PropertyGroup):
    material: bpy.props.PointerProperty(type=bpy.types.Material)

class MaterialSet(bpy.types.PropertyGroup):
    materials: bpy.props.CollectionProperty(type=MaterialItem)
    name: bpy.props.StringProperty(default="material set")
    material_set_id: bpy.props.IntProperty(min=0)

class MaterialSets(bpy.types.PropertyGroup):
    surface_names: bpy.props.CollectionProperty(type=StringItem)    
    sets: bpy.props.CollectionProperty(type=MaterialSet)    
    collapsed_panels: bpy.props.BoolVectorProperty()
    next_material_set_id: bpy.props.IntProperty(min=0)
    #surfaces_editable: bpy.props.BoolProperty(default=True)

class VariationObject(bpy.types.PropertyGroup):        
    obj:bpy.props.PointerProperty(type=bpy.types.Object) 
    name: bpy.props.StringProperty()

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
            return
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

class MeshLods(bpy.types.PropertyGroup):
    lods: bpy.props.CollectionProperty(type=MeshLod)        
    active_lod: bpy.props.IntProperty(default=0, name="active_lod", override={"LIBRARY_OVERRIDABLE"})    
    active_material_set_id: bpy.props.IntProperty(default=0, override={"LIBRARY_OVERRIDABLE"})
    material_set_count: bpy.props.IntProperty(default=0)
    lod_count: bpy.props.IntProperty(default=0)
    lods_editable: bpy.props.BoolProperty(default =True)
    material_sets_editable: bpy.props.BoolProperty(default =True)    
    variations: bpy.props.CollectionProperty(type=VariationObject)
    
    def replace_lod_mesh(self, context):
        if self.object_for_replacing_lod_mesh == None: return        
        target_lod = [lod for lod in self.lods if lod.lod == self.active_lod][0]        
        target_lod.mesh = self.object_for_replacing_lod_mesh.data     
                        
        validate_surface_count(target_lod.mesh)    
        validate_material_set_count(context.object.mesh_lods)
        validate_material_set_materials(target_lod.mesh, target_lod.mesh.material_sets.sets[0])
        
        self.object_for_replacing_lod_mesh = None        
        context.object.data = target_lod.mesh
        set_active_lod(context.object, self.active_lod)
    object_for_replacing_lod_mesh: bpy.props.PointerProperty(type=bpy.types.Object, update=replace_lod_mesh, description="Choose a mesh object to copy it's mesh into the current Lod")




######################
# ACTIVATE FUNCTIONS #
######################
def get_material_set_by_id(material_sets, id):
    return [material_set for material_set in material_sets if material_set.material_set_id == id][0]

def activate_material_set(obj, set_id):       
    material_set = get_material_set_by_id(obj.data.material_sets.sets,set_id)         
    validate_material_set_count(obj.mesh_lods)
    validate_material_set_materials(obj.data, material_set)
    if not material_set: return 
    obj.mesh_lods.active_material_set_id = material_set.material_set_id
    for i, slot in enumerate(obj.material_slots):
        if not slot.is_property_readonly("material"):            
            slot.material = material_set.materials[i].material
      

def confirm_or_make_overrides(obj,new_lod):    
    if True or (not obj.override_library and not obj.library):         
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

def set_active_lod(obj, lod):    
    if not obj.type == 'MESH': return      
    new_obj = confirm_or_make_overrides(obj,lod)    
    mesh = [x for x in new_obj.mesh_lods.lods if x.lod == lod][0].mesh        
    for x in new_obj.mesh_lods.lods:
        m = x.mesh
        if x.lod==1:
            print("AAA")
    new_obj.data = mesh
    new_obj.mesh_lods.active_lod = lod
    activate_material_set(obj, obj.mesh_lods.active_material_set_id)



########################
# VALIDATION FUNCTIONS #
########################
def get_active_lod(obj):
    return [lod for lod in obj.mesh_lods.lods if lod.lod == obj.mesh_lods.active_lod][0]

def validate_active_lod(obj):
    get_active_lod(obj).mesh = obj.data

def validate_active_material_set(obj):    
    validate_active_lod(obj)
    active_material_set = obj.data.material_sets.sets[obj.mesh_lods.active_material_set_id]
    validate_material_set_materials(obj.data, active_material_set )
    for i in range(len(active_material_set.materials)):
        #if obj.data.materials[i] != None:
        if obj.mesh_lods.material_sets_editable:
            active_material_set.materials[i].material = obj.data.materials[i]
        else:
            obj.data.materials[i] = active_material_set.materials[i].material

def validate_material_set_materials(mesh, material_set):    
    #############################
    # ensure parity for:        #
    # 1. mesh's material        #
    # 2. surface_names          #
    # 3. material_set materials #
    #############################
    for i in range(max(0, len( mesh.materials) - len(mesh.material_sets.surface_names))):
        mesh.material_sets.surface_names.add()            
    for i in range( abs(len( mesh.materials) - len(material_set.materials ))):
        if len( mesh.materials) < len(material_set.materials ):
            mesh.materials.append(None)
        else:
            material_set.materials.add()        
            if mesh.materials[i]:
                material_set.materials[-1].material = mesh.materials[i]    
                mesh.material_sets.surface_names[i].value = mesh.materials[i].name
            else:
                mesh.material_sets.surface_names[i].value = "surface"


def validate_material_set_count(obj_mesh_lods):        
    set_count_data = []    
    obj_mesh_lods.material_set_count = max( obj_mesh_lods.material_set_count, 1)
    for i,lod in enumerate(obj_mesh_lods.lods):
        set_count_data.append({"lod": lod, "count": len(lod.mesh.material_sets.sets)})
        obj_mesh_lods.material_set_count = max(obj_mesh_lods.material_set_count, set_count_data[i]['count'])    
    for lod in [data['lod'] for data in set_count_data if data['count'] < obj_mesh_lods.material_set_count ]:        
        material_set = lod.mesh.material_sets.sets.add() 
        i = 0
        while get_material_set_by_id(lod.mesh.material_sets, i):
            i+= 1
        material_set.material_set_id = i                                
        material_set.name = "set " + str(i)


def validate_surface_count(mesh):    
    for i in range( max(1, abs(len(mesh.materials) - len(mesh.material_sets.surface_names)) )):    
        if len(mesh.materials) < len(mesh.material_sets.surface_names):    
            mesh.materials.append(None)
        else:
            mesh.material_sets.surface_names.add()
            mesh.material_sets.surface_names[-1].value = "surface"