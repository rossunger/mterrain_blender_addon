import bpy
import bmesh
import math
import numpy
import mathutils

class MTerrain_OT_prepare_tilemap_for_painting(bpy.types.Operator):
    bl_idname = "mterrain.prepare_tilemap_for_painting"
    bl_label = "prepare_tilemap_for_painting"
    bl_options = {'REGISTER','PRESET', 'UNDO'}
    size: bpy.props.IntProperty(default=50)
    
    def execute(self, context):          
        i = self.size              
        obj = bpy.data.objects.new("new_house", bpy.data.meshes.new("new_house"))
        context.scene.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)        
        obj.show_wire = True
        bpy.ops.object.mode_set(mode='EDIT')   
        if not context.mode in ["EDIT", "EDIT_MESH"]:
            print("\n\naaaaaaaaaaaaaa")
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=i, y_subdivisions=i, size=i )            
        bpy.ops.mesh.poke()
        node_group = remove_verices_with_attribute_node_group()
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.modifiers.new("temp", type="NODES")            
        obj.modifiers[0].node_group = node_group
        obj.modifiers[0].show_viewport = False
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')
        bpy.ops.brush.curve_preset(shape="MAX")
        context.scene.tool_settings.unified_paint_settings.size = 10
        bpy.ops.geometry.color_attribute_add(name="house_tilemap", color=(1.,1.,1.,1.))        
        mat = bpy.data.materials.new(name = "house_grid_vertex_paint")
        mat.use_nodes = True
        #mat.node_tree = make_house_grid_vertex_paint_material_node_group(mat)
        obj.data.materials.append(mat) 
        obj['tilemap_library'] = 'D:\\GAMEDEV\\Blender\\addons\\Ross\\MTerrain_Tools\\DemoAssets\\ModularBuildings.blend'
        return {'FINISHED'}

class MTerrain_OT_convert_tilemap_to_instances(bpy.types.Operator):
    bl_idname = "mterrain.convert_tilemap_to_instances"
    bl_label = "convert_tilemap_to_instances"
    bl_options = {'REGISTER','PRESET', 'UNDO'}
            
    def execute(self, context):                        
        convert_tilemap_to_instances(context)
        return {'FINISHED'}

def make_house_grid_vertex_paint_material_node_group(mat):    
    house_grid_vertex_paint = mat.node_tree
    #start with a clean node tree
    for node in house_grid_vertex_paint.nodes:
        house_grid_vertex_paint.nodes.remove(node)
    
    principled_bsdf = house_grid_vertex_paint.nodes.new("ShaderNodeBsdfPrincipled")    
    
    #node Material Output
    material_output = house_grid_vertex_paint.nodes.new("ShaderNodeOutputMaterial")
    material_output.name = "Material Output"
    material_output.is_active_output = True    
    
    #node Color Attribute
    color_attribute = house_grid_vertex_paint.nodes.new("ShaderNodeVertexColor")
    color_attribute.name = "Color Attribute"
    color_attribute.warning_propagation = 'ALL'
    color_attribute.layer_name = "house_tilemap"

    #node RGB Curves
    rgb_curves = house_grid_vertex_paint.nodes.new("ShaderNodeRGBCurve")
    rgb_curves.name = "RGB Curves"            
    #curve 3
    rgb_curves_curve_3 = rgb_curves.mapping.curves[3]
    rgb_curves_curve_3_point_1 = rgb_curves_curve_3.points[1]
    rgb_curves_curve_3_point_1.location = (0.9854545593261719, 0.0)
    rgb_curves_curve_3_point_1.handle_type = 'VECTOR'    
    #update curve after changes
    rgb_curves.mapping.update()    
    #initialize house_grid_vertex_paint links
    #principled_bsdf.BSDF -> material_output.Surface
    house_grid_vertex_paint.links.new(principled_bsdf.outputs[0], material_output.inputs[0])
    #rgb_curves.Color -> principled_bsdf.Base Color
    house_grid_vertex_paint.links.new(rgb_curves.outputs[0], principled_bsdf.inputs[0])
    #color_attribute.Color -> rgb_curves.Color
    house_grid_vertex_paint.links.new(color_attribute.outputs[0], rgb_curves.inputs[1])
    return house_grid_vertex_paint

#initialize remove_verices_with_attribute node group
def remove_verices_with_attribute_node_group():
    remove_verices_with_attribute = bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "remove_verices_with_attribute")
    remove_verices_with_attribute.is_modifier = True

    #remove_verices_with_attribute interface
    #Socket Geometry
    geometry_socket = remove_verices_with_attribute.interface.new_socket(name = "Geometry", in_out='OUTPUT', socket_type = 'NodeSocketGeometry')
    geometry_socket.attribute_domain = 'POINT'
    #Socket Geometry
    geometry_socket_1 = remove_verices_with_attribute.interface.new_socket(name = "Geometry", in_out='INPUT', socket_type = 'NodeSocketGeometry')
    geometry_socket_1.attribute_domain = 'POINT'
    #Socket Attribute Name
    attribute_name_socket = remove_verices_with_attribute.interface.new_socket(name = "Attribute Name", in_out='INPUT', socket_type = 'NodeSocketString')
    attribute_name_socket.default_value = "house_tilemap"
    attribute_name_socket.subtype = 'NONE'
    attribute_name_socket.attribute_domain = 'POINT'
    #initialize remove_verices_with_attribute nodes
    #node Group Input
    group_input = remove_verices_with_attribute.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"
    #node Group Output
    group_output = remove_verices_with_attribute.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    #node Named Attribute
    named_attribute = remove_verices_with_attribute.nodes.new("GeometryNodeInputNamedAttribute")
    named_attribute.name = "Named Attribute"
    named_attribute.data_type = 'FLOAT'

    #node Separate Geometry
    separate_geometry = remove_verices_with_attribute.nodes.new("GeometryNodeSeparateGeometry")
    separate_geometry.name = "Separate Geometry"
    separate_geometry.domain = 'POINT'
    
    #group_input.Geometry -> separate_geometry.Geometry
    remove_verices_with_attribute.links.new(group_input.outputs[0], separate_geometry.inputs[0])
    #named_attribute.Attribute -> separate_geometry.Selection
    remove_verices_with_attribute.links.new(named_attribute.outputs[0], separate_geometry.inputs[1])
    #group_input.Attribute Name -> named_attribute.Name
    remove_verices_with_attribute.links.new(group_input.outputs[1], named_attribute.inputs[0])
    #separate_geometry.Selection -> group_output.Geometry
    remove_verices_with_attribute.links.new(separate_geometry.outputs[0], group_output.inputs[0])
    return remove_verices_with_attribute

def convert_tilemap_to_instances(context):
    if len(context.object.modifiers) ==1:
        original_modifier = context.object.modifiers[0]
    context.object.select_set(False)
    tilemap_library_path = context.object['tilemap_library']
    obj = bpy.data.objects.new(context.object.name, context.object.data.copy())    
    context.scene.collection.objects.link(obj)
    context.view_layer.objects.active = obj    
    with context.temp_override(object= obj, active_object =obj):
        new_modifier = obj.modifiers.new(name="AAA", type='NODES')
        new_modifier.node_group = original_modifier.node_group.copy()
        obj.select_set(True)
        bpy.ops.object.modifier_apply(modifier=new_modifier.name)
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)   
        for vert in bm.verts:
            if abs(math.remainder(vert.co[0],1)) > 0.01 or abs(math.remainder(vert.co[1],1)) > 0.01:        
                vert.select_set(True)
            else:
                vert.select_set(False)    
        bpy.ops.mesh.dissolve_verts()
        bmesh.update_edit_mesh(obj.data)
        validate_modular_objects(tilemap_library_path)
        build_house(context)
        bpy.ops.object.mode_set(mode='OBJECT')
        #bpy.data.objects.remove(obj)

def validate_modular_objects(library_path):
    obj_list = ['roof_angle', 'roof_angle_filler', 'roof_corner_inside', 'roof_corner_middle', 'roof_straight', 'roof_middle', 'roof_middle_flat', 'roof_corner_middle_inverted', 'roof_straight_to_angle_filler', 'roof_corner_middle_flat', 'roof_corner_outside', 'roof_angle_joiner', 'wall_straight', 'wall_straight_window_big', 'wall_straight_window_high', 'wall_straight_door', 'wall_corner_inside', 'wall_internal_none', 'wall_internal_straight', 'wall_internal_corner', 'wall_internal_angle', 'wall_internal_angle_corner', 'wall_straight_angle_connector_both', 'wall_straight_angle_connector', 'wall_angle_filler_inside', 'wall_angle', 'wall_angle_filler_outside', 'wall_corner_outside', 'wall_angle_joiner']
    for name in obj_list:
        if not name in bpy.data.objects:
            with bpy.data.libraries.load(library_path, assets_only = True, link = True) as (data_from, data_to):
                for i, obj in enumerate(data_from.objects):                
                    if obj in obj_list:
                        data_to.objects.append(data_from.objects[i])                                        
            break
    for name in obj_list:
        if bpy.data.objects[name].library:
            bpy.data.objects[name].override_create()
        elif bpy.data.objects[name].override_library:
            print(name, ": overridelibrary")
        else:
            print(name, ": aaaaaaaa")
def build_house(context):
    if context.object.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
            
    obj_name = context.object.name        
    if not "House1" in bpy.data.collections:
        house_collection = bpy.data.collections.new("House1")
        context.scene.collection.children.link(house_collection)
    house = bpy.data.collections["House1"]
    grid = bmesh.from_edit_mesh(bpy.data.objects[obj_name].data)

    add_roof = True #False

    for obj in house.objects:
        bpy.data.objects.remove(obj)

    for vert in grid.verts:
        vert.select_set(False)
    for face in grid.faces:
        face.select_set(False)

    def get_5(the_face):
        total_area = the_face.calc_area()
        all_verts = []
        faces = [the_face]
        for edge in the_face.edges:
            for face in edge.link_faces:
                if face in faces: continue
                total_area += face.calc_area()
                faces.append(face)
                for vert in face.verts:
                    if not vert in all_verts:
                        all_verts.append(vert)
        return total_area, all_verts, faces
        
        
    def get_9(the_face):   
        total_area = the_face.calc_area()
        all_verts = []    
        faces = [the_face]
        for vert in the_face.verts:
            all_verts.append(vert)
            for face in grid.faces:
                if face in faces: continue
                if vert in face.verts:
                    all_verts.append(vert)
                    total_area += face.calc_area()    
                    faces.append(face)    
        return round(total_area, 1), all_verts, faces

    def select_straight_single():
        for face in grid.faces:
            area, verts,faces = get_5(face)
            if len(faces) != 4: continue
            edge = [e for e in face.edges if len(e.link_faces)==1][0] #get the one edge that's not connected to other faces

            other_verts = [vert for vert in face.verts if not vert in edge.verts]  # the verts parallel to the outside edge

            is_vertical = abs(other_verts[0].co[0] - other_verts[1].co[0]) < 0.1
            is_up = other_verts[0].co[1] < edge.verts[0].co[1]                    
            is_left = other_verts[0].co[0] < edge.verts[0].co[0]                    

            connected_angle_faces = []
            for vert in edge.verts:
                for f in vert.link_faces:
                    if len(f.verts) != 3:continue            
                    tangent_vert = [v for v in f.verts if abs(v.co[0] - vert.co[0]) >0.01 and abs(v.co[1] - vert.co[1]) >0.01][0]
                    is_connected_angle_face = False
                    if not is_vertical:
                        if is_up and tangent_vert.co[1] > vert.co[1]:
                            is_connected_angle_face = True                     
                        elif not is_up and tangent_vert.co[1] < vert.co[1]:
                            is_connected_angle_face = True
                    else:
                        if is_left and tangent_vert.co[0] > vert.co[0]:
                            is_connected_angle_face = True
                        elif not is_left and tangent_vert.co[0] < vert.co[0]:
                            is_connected_angle_face = True

                    if is_connected_angle_face: 
                        connected_angle_faces.append(f)

            if len(connected_angle_faces) == 2:
                obj = bpy.data.objects["wall_straight_angle_connector_both"].copy()
                house.objects.link(obj)
                obj.location = (edge.verts[0].co + edge.verts[1].co)/2 
                if is_vertical:
                    if is_left:              
                        obj.location.y-= 0.5
                        obj.rotation_euler[2] = math.pi *0.5                                 
                    else:
                        obj.location.y+= 0.5
                        obj.rotation_euler[2] = math.pi * -0.5                    
                else:
                    if is_up:              
                        obj.location.x+= 0.5
                        obj.rotation_euler[2] = math.pi
                    else:
                        obj.location.x-= 0.5                
                if add_roof:
                    roof_obj = bpy.data.objects["roof_straight"].copy()
                    house.objects.link(roof_obj)
                    roof_obj.location = obj.location
                    roof_obj.location[2] += 3
                    roof_obj.scale = obj.scale
                    roof_obj.rotation_euler = obj.rotation_euler                                
                continue
            elif len(connected_angle_faces) == 1:                 
                obj = bpy.data.objects["wall_straight_angle_connector"].copy()
                house.objects.link(obj)
                obj.location = (edge.verts[0].co + edge.verts[1].co)/2 
                
                shared_vert = [v for v in edge.verts if v in connected_angle_faces[0].verts][0]
                tangent_vert = [v for v in connected_angle_faces[0].verts if abs(v.co[0]-shared_vert.co[0]) >0.01 and abs(v.co[1]-shared_vert.co[1]) >0.01][0]
                if is_vertical:
                    is_up = tangent_vert.co[1] < shared_vert.co[1]
                    if is_up:                    
                        #shared_vert.select_set(True)              
                        if is_left:
                            obj.location.y-= 0.5
                            obj.rotation_euler[2] = math.pi *0.5                                 
                        else:      
                            obj.scale.x =-1
                            obj.location.y-= 0.5
                            obj.rotation_euler[2] = math.pi * -0.5                    
                    else:
                        if is_left:
                            obj.scale.x =-1                        
                            obj.location.y+= 0.5
                            obj.rotation_euler[2] = math.pi *0.5                                 
                        else:                        
                            obj.location.y+= 0.5
                            obj.rotation_euler[2] = math.pi * -0.5                                                
                else:
                    is_left = tangent_vert.co[0] < vert.co[0]
                    if is_left:
                        if is_up:                                      
                            obj.scale.x =-1                            
                            obj.location.x-= 0.5
                            obj.rotation_euler[2] = math.pi
                        else:                   
                            obj.location.x-= 0.5                
                    else:
                        if is_up:                                     
                            obj.location.x+= 0.5
                            obj.rotation_euler[2] = math.pi
                        else:
                            obj.scale.x =-1                                                    
                            obj.location.x+= 0.5                
                if add_roof:
                    roof_obj = bpy.data.objects["roof_straight"].copy()
                    house.objects.link(roof_obj)
                    roof_obj.location = obj.location
                    roof_obj.location[2] += 3
                    roof_obj.scale = obj.scale
                    roof_obj.rotation_euler = obj.rotation_euler                                
                continue
                    
            obj = bpy.data.objects["wall_straight"].copy()
            house.objects.link(obj)
            obj.location = (edge.verts[0].co + edge.verts[1].co)/2 
            if is_vertical: 
                obj.rotation_euler[2] = math.pi/2                                        
                if not is_left: 
                    obj.scale.y =-1
                obj.location.y-=0.5
            else:                    
                obj.location.x -= 0.5
                if is_up:
                    obj.scale.y = -1
            obj.location.z = 0
            if add_roof:
                roof_obj = bpy.data.objects["roof_straight"].copy()
                house.objects.link(roof_obj)
                roof_obj.location = obj.location
                roof_obj.location[2] += 3
                roof_obj.scale = obj.scale
                roof_obj.rotation_euler = obj.rotation_euler

    def select_angle():
        for face in grid.faces:
            if len(face.verts) != 3: continue
            obj = bpy.data.objects["wall_angle"].copy()
            house.objects.link(obj)

            tangent_edge = [edge for edge in face.edges if len(edge.link_faces) == 1][0]
            corner_vert = [vert for vert in face.verts if not vert in tangent_edge.verts][0]                                        
            first_vert = tangent_edge.verts[0] if tangent_edge.verts[0].co[0] < tangent_edge.verts[1].co[0] else tangent_edge.verts[1]
            second_vert = [vert for vert in tangent_edge.verts if vert != first_vert][0]
            obj.location = first_vert.co   
            if first_vert.co[1] < second_vert.co[1]:
                obj.scale.y = -1
                if abs(corner_vert.co[0] - min(first_vert.co[0], second_vert.co[0])) < 0.1:                    
                    obj.location.y +=1                
                elif abs(corner_vert.co[0] - max(first_vert.co[0], second_vert.co[0])) <0.1:
                    obj.rotation_euler[2] += math.pi
                    obj.location.x +=1
            else:                               
                if abs(corner_vert.co[0] - min(first_vert.co[0], second_vert.co[0])) < 0.1:                    
                    obj.location.y -=1
                    #obj.scale.x=0
                elif abs(corner_vert.co[0] - max(first_vert.co[0], second_vert.co[0])) < 0.1:
                    obj.rotation_euler[2] += math.pi                   
                    obj.location.x += 1
                    pass
            obj.location.z = 0
            
            if add_roof:
                roof_obj = bpy.data.objects["roof_angle"].copy()
                house.objects.link(roof_obj)
                roof_obj.location = obj.location
                roof_obj.location[2] += 3
                roof_obj.scale = obj.scale
                roof_obj.rotation_euler = obj.rotation_euler        
            
            # now add the angle fillers
            for vert in tangent_edge.verts:
                other_faces = [other_face for other_face in grid.faces if other_face != face and vert in other_face.verts]
                #############################################
                # 2 angles touching to form a straight line #
                #############################################
                if len(other_faces) ==2:
                    for other_face in other_faces:
                        if len(other_face.verts) != 3: continue
                        if vert.co[1] > min ( [v.co[1] for v in other_face.verts] ):
                            obj = bpy.data.objects["wall_angle_joiner"].copy()
                            house.objects.link(obj)
                            obj.location = vert.co

                            other_vert = [v for v in other_face.verts if abs(v.co[0] - vert.co[0]) >0.1 and abs(v.co[1] - vert.co[1]) >0.1][0]
                            corner_vert = [v for v in other_face.verts if not v in [other_vert, vert]][0]
                            is_left = other_vert.co[0] < vert.co[0]
                            is_down = corner_vert.co[1] < vert.co[1]
                            if is_down:
                                if is_left:
                                    obj.rotation_euler[2]-=math.pi*-0.5                               
                                else:
                                    pass                                                                                                                         
                            else:                            
                                if is_left:
                                    obj.rotation_euler[2]-=math.pi*0.5
                                else:
                                    obj.rotation_euler[2]+=math.pi
                            if add_roof:
                                roof_obj = bpy.data.objects["roof_angle_joiner"].copy()
                                house.objects.link(roof_obj)
                                roof_obj.location = obj.location
                                roof_obj.location[2] += 3
                                roof_obj.scale = obj.scale
                                roof_obj.rotation_euler = obj.rotation_euler
                            
                if len(other_faces) ==1:
                    ################################
                    # 2 angles meeting at a corner #
                    ################################
                    if round(other_faces[0].calc_area(),1) < 1.0:               
                        obj = bpy.data.objects["wall_angle_joiner"].copy()
                        house.objects.link(obj)
                        obj.location = vert.co
                        tangent_vert = [v for v in other_faces[0].verts if abs(v.co[0] - vert.co[0]) >0.01 and abs(v.co[1] - vert.co[1]) > 0.01][0]
                        corner_vert = [v for v in other_faces[0].verts if not v in [tangent_vert, vert]][0]
                        is_vertical = abs(tangent_vert.co[0] - corner_vert.co[0]) < 0.01
                        is_left = tangent_vert.co[0] > vert.co[0]
                        is_up = tangent_vert.co[1] < vert.co[1] 
                        if is_vertical:
                            if is_up:
                                if is_left:
                                    pass
                                else:
                                    obj.rotation_euler.z = math.pi *0.5                                                            
                            else:
                                if is_left:
                                    obj.rotation_euler.z = math.pi *-0.5                                                            
                                else:
                                    obj.rotation_euler.z = math.pi                                                                                            
                        else:
                            if is_up:
                                if is_left:
                                    obj.rotation_euler.z = math.pi *-0.5
                                else:
                                    obj.rotation_euler.z = math.pi                                
                            else:    
                                if is_left:
                                    pass
                                else:
                                    obj.rotation_euler.z = math.pi * 0.5                                
                        
                        if add_roof:
                            roof_obj = bpy.data.objects["roof_angle_joiner"].copy()
                            house.objects.link(roof_obj)
                            roof_obj.location = obj.location
                            roof_obj.location[2] += 3
                            roof_obj.scale = obj.scale
                
                    ###############################
                    # An angle meeting a straight #
                    ###############################
                    elif round(other_faces[0].calc_area(),1) == 1.0:               
                        obj = bpy.data.objects["wall_angle_filler_inside"].copy()
                        house.objects.link(obj)
                        obj.location = vert.co

                        long_edge = [edge for edge in vert.link_edges if edge.calc_length() > 1.01][0]
                        new_vert = long_edge.verts[0] if long_edge.verts[0] != vert else long_edge.verts[1]
                        other_edge = None
                        for edge in vert.link_edges:
                            if edge == long_edge: continue
                            for edge_vert in edge.verts:
                                if edge_vert == vert: continue
                                if abs(edge_vert.co[0] - new_vert.co[0]) >0.01 and abs(edge_vert.co[1] - new_vert.co[1]) >0.01:
                                    other_edge = edge
                        is_horizontal = abs(other_edge.verts[0].co[0] - other_edge.verts[1].co[0]) > 0.1
                        is_above = new_vert.co[1] > other_edge.verts[0].co[1] 
                        is_left = new_vert.co[0] < other_edge.verts[0].co[0] 
                        if not is_horizontal:
                            if is_above:
                                if is_left:
                                    obj.scale.x = -1
                                    obj.rotation_euler.z -= math.pi *0.5                                
                                else:
                                    obj.rotation_euler.z -= math.pi *-0.5                                
                            else:
                                if is_left:
                                    obj.rotation_euler.z -= math.pi *0.5                                                                
                                else:
                                    obj.scale.x = -1
                                    obj.rotation_euler.z -= math.pi *-0.5
                        else:
                            if is_above:
                                if is_left:
                                    obj.rotation_euler.z += math.pi                                
                                else:
                                    obj.scale.x = -1                                                                                          
                                    obj.rotation_euler.z += math.pi                                
                            else:
                                if is_left:                                                                
                                    obj.scale.x = -1                                    
                                else:                                                                
                                    pass
                        if add_roof:
                            roof_obj = bpy.data.objects["roof_angle_joiner"].copy()
                            house.objects.link(roof_obj)
                            roof_obj.location = obj.location
                            roof_obj.location[2] += 3
                            roof_obj.scale = obj.scale
                            roof_obj.rotation_euler.z = obj.rotation_euler.z
                                                            

    def select_corner_inside():
        for face in grid.faces:
            area, verts, faces = get_9(face)
            for vert in face.verts:
                if len(vert.link_edges) != 2: continue                
                is_top = True
                is_left= True
                for face_vert in face.verts:                    
                    if vert.co[0] > face_vert.co[0]:
                        is_left = False
                    if vert.co[1] < face_vert.co[1]:
                        is_top = False
                obj = bpy.data.objects["wall_corner_inside"].copy()    
                house.objects.link(obj)
                obj.location = vert.co
                if is_top and is_left:
                    obj.rotation_euler.z= math.pi
                    obj.location.x+=1
                if is_top and not is_left:
                    obj.rotation_euler.z= math.pi/2
                    obj.location.y-=1
                if not is_top and is_left:
                    obj.rotation_euler.z= math.pi/-2
                    obj.location.y+=1
                if not is_top and not is_left:
                    obj.location.x-=1
                obj.location.z = 0        

                ############
                ### ROOF ###
                ############
                if add_roof:
                    roof_obj = bpy.data.objects["roof_corner_inside"].copy()
                    house.objects.link(roof_obj)
                    roof_obj.location = obj.location
                    roof_obj.location[2] += 3
                    roof_obj.scale = obj.scale
                    roof_obj.rotation_euler = obj.rotation_euler
                    
                
                #### FILLER PIECES #####
                for vert in face.verts:
                    if len(vert.link_edges)==2: continue
                    for edge in vert.link_edges:
                        if edge.calc_length() <= 1.01 : continue
                        obj = bpy.data.objects["wall_angle_filler_outside"].copy()
                        house.objects.link(obj)
                        
                        shared_vert = [v for v in edge.verts if v in face.verts][0]
                        other_vert = [v for v in face.verts if len(v.link_edges)==2][0]    
                        tangent_vert = [v for v in edge.verts if v != shared_vert][0]
                        obj.location = vert.co
                        other_corner_vert = None
                        for e in other_vert.link_edges:
                            for v in e.verts:
                                if v == other_vert: continue
                                other_corner_vert = v
                        if abs(other_corner_vert.co[0]- tangent_vert.co[0]) < 0.01 or abs(other_corner_vert.co[1]- tangent_vert.co[1]) < 0.01:
                            continue


                        is_vertical = abs(shared_vert.co[0] - other_vert.co[0])< 0.01
                        if not is_vertical:
                            if is_top:
                                if is_left:
                                    obj.rotation_euler.z = math.pi *-0.5
                                else:
                                    obj.rotation_euler.z = math.pi *0.5
                                    obj.scale.x=-1
                            else:
                                if is_left:
                                    obj.rotation_euler.z = math.pi *-0.5
                                    obj.scale.x=-1
                                else:
                                    obj.rotation_euler.z = math.pi *0.5
                        else:
                            if is_top:
                                if is_left:
                                    obj.rotation_euler.z = math.pi 
                                    obj.scale.x=-1
                                else:
                                    obj.rotation_euler.z = math.pi                                 
                            else:
                                if is_left:                                
                                    pass
                                else:
                                    obj.scale.x=-1

                        if add_roof:
                            roof_obj = bpy.data.objects["roof_angle_filler"].copy()
                            house.objects.link(roof_obj)
                            roof_obj.location = obj.location
                            roof_obj.location[2] += 3
                            roof_obj.scale = obj.scale
                            roof_obj.rotation_euler = obj.rotation_euler       
                            roof_obj.rotation_euler.z += math.pi*0.5



    def select_straight_angle_connector():
        pass
    def select_straight_angle_connector_both():
        pass

    ############
    # INTERNAL #
    ############
    def select_internal_none():
        for face in grid.faces:
            area, verts, faces = get_5(face)
            if len(faces)==5:                                
                bottom_left_vert =face.verts[0]
                for v in face.verts:     
                    if v == bottom_left_vert: continue                    
                    if v.co.x+v.co.y < bottom_left_vert.co.x + bottom_left_vert.co.y:
                        bottom_left_vert = v
                bottom_left_vert.select_set(True)
                obj = bpy.data.objects["wall_internal_none"].copy()
                house.objects.link(obj)
                obj.location = bottom_left_vert.co
                #obj.location.y-=1
                #obj.location.x-=1
                if add_roof:                    
                    roof_obj = bpy.data.objects["roof_middle_flat"].copy()
                    house.objects.link(roof_obj)
                    roof_obj.location = obj.location
                    roof_obj.location[2] +=3.7
                    roof_obj.scale = obj.scale
                    roof_obj.rotation_euler = obj.rotation_euler            
        #bpy.data.objects["wall_internal_straight"]
        #bpy.data.objects["wall_internal_none"]
        #bpy.data.objects["wall_internal_corner"]
        #bpy.data.objects["wall_internal_angle_corner"]
        #bpy.data.objects["wall_internal_angle"]

    select_angle()
    select_corner_inside()
    select_straight_single()
    select_internal_none()

    bmesh.update_edit_mesh(bpy.data.objects[obj_name].data)

    bpy.data.objects.remove(context.object)











