# Copyright (C) 2024 Wildfire Games.
# This file is part of 0 A.D.
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
import bpy_extras
import os
from . import MaxColladaFixer

class ImportPyrogenesisActor(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Load a Pyrogenesis actor file"""
    bl_label = "Import Pyrogenesis Actor"
    bl_idname = 'import_pyrogenesis_scene.xml'
    currentPath = ""
    filter_glob:  bpy.props.StringProperty(
        default="*.xml", 
        options={'HIDDEN'}
    ) # type: ignore

    import_props: bpy.props.BoolProperty(
        name='Import props',
        description='Whether to include props in the importation.',
        default=True
    ) # type: ignore

    import_textures: bpy.props.BoolProperty(
        name='Import textures',
        description='Whether to include textures in the importation.',
        default=True
    ) # type: ignore

    import_depth: bpy.props.IntProperty(
        name='Import Depth',
        description='How much prop depth there should be',
        default=-1
    ) # type: ignore

    def draw(self, context):
        layout = self.layout

        layout.prop(self, 'import_props')
        layout.prop(self, 'import_textures')
        layout.prop(self, 'import_depth')

    def execute(self, context):
        return self.import_pyrogenesis_actor(context)

    def find_parent_armature(self, bone):
        for armature in bpy.data.armatures:
            for armature_bone in armature.bones:
                if bone.name == armature_bone.name:
                    for obj in bpy.data.objects:
                        if hasattr(obj, 'data') and hasattr(obj.data, 'name') and obj.data.name == armature.name:
                             return obj

        return None

    def set_copy_transform_constraint(self, obj, parent):
        """Set constraints for props so that they fit their prop point."""

        if(str(type(parent)) == '<class \'bpy_types.Bone\'>'):
            armature = self.find_parent_armature(parent)
            print(obj.name + " -> " + armature.name +  " -> " + parent.name)
            constraint = obj.constraints.new('COPY_LOCATION')
            constraint.show_expanded = False
            constraint.mute = False
            constraint.target = armature
            constraint.subtarget = parent.name
            constraint2 = obj.constraints.new('COPY_ROTATION')
            constraint2.show_expanded = False
            constraint2.mute = False
            constraint2.target = armature
            constraint2.subtarget = parent.name
            return

        print(obj.name + " -> " + parent.name)
        constraint = obj.constraints.new('COPY_LOCATION')
        constraint.show_expanded = False
        constraint.mute = False
        constraint.target = parent
        constraint2 = obj.constraints.new('COPY_ROTATION')
        constraint2.show_expanded = False
        constraint2.mute = False
        constraint2.target = parent
        obj.parent = parent

    def create_new_material(self, textures, material):
        mname = None
        for texture in textures:
            if texture.split('|')[0] == 'baseTex':
                mname = os.path.basename(texture.split('|')[1])
                break

        if mname is None:
            mname = os.path.basename(textures[0].split('|')[1])

        if (bpy.data.materials.get(mname) is not None):
            return mname

        mat = bpy.data.materials.new(name= mname)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]

        for texture in textures:
            fname = os.path.basename(texture.split('|')[1])
            print(fname)
            if fname not in bpy.data.images:
                continue

            texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
            texImage.image = bpy.data.images[fname]
            if texture.split('|')[0] == 'baseTex':
                mat.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])

                if 'player_trans' in material:
                    color_node = mat.node_tree.nodes.new('ShaderNodeRGB')
                    color_node.outputs[0].default_value = (1, 0.213477, 0.0543914, 1)
                    multiply_node = mat.node_tree.nodes.new('ShaderNodeMixRGB')
                    multiply_node.blend_type = 'MULTIPLY'
                    invert_node = mat.node_tree.nodes.new('ShaderNodeInvert')
                    mat.node_tree.links.new(invert_node.inputs['Color'], texImage.outputs['Alpha'])
                    mat.node_tree.links.new(multiply_node.inputs[1], texImage.outputs['Color'])
                    mat.node_tree.links.new(multiply_node.inputs[2], color_node.outputs['Color'])
                    mat.node_tree.links.new(multiply_node.inputs[0], invert_node.outputs['Color'])
                    mat.node_tree.links.new(bsdf.inputs['Base Color'], multiply_node.outputs['Color'])

                elif 'basic_trans' in material:
                    mix_shader_node = mat.node_tree.nodes.new('ShaderNodeMixShader')
                    transparent_node = mat.node_tree.nodes.new('ShaderNodeBsdfTransparent')
                    mat.node_tree.links.new(mix_shader_node.inputs[0], texImage.outputs['Alpha'])
                    mat.node_tree.links.new(mix_shader_node.inputs[2], bsdf.outputs['BSDF'])
                    mat.node_tree.links.new(mix_shader_node.inputs[1], transparent_node.outputs['BSDF'])

                    output_node = mat.node_tree.nodes.get("Material Output")
                    mat.node_tree.links.new(output_node.inputs['Surface'], mix_shader_node.outputs['Shader'])
                    mat.blend_method = 'CLIP'

                continue

            if texture.split('|')[0] == 'normTex':
                texImage.image.colorspace_settings.name='Non-Color'
                normal_node = mat.node_tree.nodes.new('ShaderNodeNormalMap')
                separate_node = mat.node_tree.nodes.new('ShaderNodeSeparateXYZ')
                invert_node = mat.node_tree.nodes.new('ShaderNodeInvert')
                join_node = mat.node_tree.nodes.new('ShaderNodeCombineXYZ')

                mat.node_tree.links.new(separate_node.inputs['Vector'], texImage.outputs['Color'])
                #Direct X normals need to have their Y channel inverted for OpenGL
                mat.node_tree.links.new(invert_node.inputs['Color'], separate_node.outputs['Y'])
                mat.node_tree.links.new(join_node.inputs['X'], separate_node.outputs['X'])
                mat.node_tree.links.new(join_node.inputs['Z'], separate_node.outputs['Z'])
                mat.node_tree.links.new(join_node.inputs['Y'], invert_node.outputs['Color'])
                mat.node_tree.links.new(normal_node.inputs['Color'], join_node.outputs['Vector'])
                mat.node_tree.links.new(bsdf.inputs['Normal'], normal_node.outputs['Normal'])
                continue


            if texture.split('|')[0] == 'specTex':
                texImage.image.colorspace_settings.name='Non-Color'
                mat.node_tree.links.new(bsdf.inputs['Specular IOR Level'], texImage.outputs['Color'])

        return mat.name

    def assign_material_to_object(self, ob, material_name):
        """Assigns a given material name to an object."""

        # Get any exiting material with that name
        mat = bpy.data.materials.get(material_name)
        if mat is None:
            # No material, create.
            mat = bpy.data.materials.new(name=material_name)
        if ob.data.materials:
            # Assign to 1st material slot.
            ob.data.materials[0] = mat
        else:
            # No slots, append.
            ob.data.materials.append(mat)

    def import_pyrogenesis_actor(self, context):
        import xml.etree.ElementTree as ET
        print('loading ' + self.filepath + '...')

        self.currentPath = (self.filepath[0:self.filepath.find('actors')]).replace("\\", "/")
        root = ET.parse(self.filepath).getroot()
        self.parse_actor(root)

        return {'FINISHED'}
    def create_custom_mesh(self, objname, px, py, pz, width, depth):
        # Define arrays for holding data
        myvertex = []
        myfaces = []

        # Create all Vertices

        # vertex 0
        mypoint = [(-width/2, -depth/2, 0.01)]
        myvertex.extend(mypoint)

        # vertex 1
        mypoint = [(width/2, -depth/2, 0.01)]
        myvertex.extend(mypoint)

        # vertex 2
        mypoint = [(-width/2, depth/2, 0.01)]
        myvertex.extend(mypoint)

        # vertex 3
        mypoint = [(width/2, depth/2, 0.01)]
        myvertex.extend(mypoint)

        # -------------------------------------
        # Create all Faces
        # -------------------------------------
        myface = [(0, 1, 3, 2)]
        myfaces.extend(myface)

        # Generate mesh data
        mymesh = bpy.data.meshes.new(objname)
        mymesh.from_pydata(myvertex, [], myfaces)
        # Calculate the edges
        mymesh.update(calc_edges=True)
        myobject = bpy.data.objects.new(objname, mymesh)
        # Set Location
        myobject.location.x = px
        myobject.location.y = py
        myobject.location.z = pz
        scene = bpy.context.scene
        scene.collection.objects.link(myobject)

        return myobject

    def get_element_from_variant(self, root, name):
        import xml.etree.ElementTree as ET
        for child in root:
            if child.tag == name:
                return child

        # No mesh was found in this variant.
        if 'file' in root.attrib is not None:
            variantParent = ET.parse(self.currentPath + 'variants/' +  root.attrib['file']).getroot()
            return self.get_element_from_variant(variantParent, name)

        return None

    def get_mesh_from_variant(self, root):
        return self.get_element_from_variant(root, 'mesh')

    def get_textures_from_variant(self, root):
        import xml.etree.ElementTree as ET
        child_textures = None
        for child in root:
            if child.tag == 'textures':
                child_textures = child

        if 'file' in root.attrib is not None:
            variantParent = ET.parse(self.currentPath + 'variants/' +  root.attrib['file']).getroot()
            parent_textures = self.get_textures_from_variant(variantParent)
            if parent_textures is not None and child_textures is not None:
                for texture in child_textures:
                    parent_textures.append(texture)
                return parent_textures
            else:
                return child_textures


        return child_textures

    def get_props_from_variant(self, root):
        import xml.etree.ElementTree as ET

        childProps = None
        for child in root:
            if child.tag == 'props':
                childProps = child
                break


        if 'file' in root.attrib is not None:
            variantParent = ET.parse(self.currentPath + 'variants/' +  root.attrib['file']).getroot()
            parentProps = self.get_props_from_variant(variantParent)
            if parentProps is not None and childProps is not None:
                for prop in childProps:
                    parentProps.append(prop)
                return parentProps
            else:
                return childProps

        return childProps

    def parse_actor(self, root, proppoint="root", parentprops=[], rootObj=None, propDepth=0):
        import xml.etree.ElementTree as ET
        import bpy
        import random
        import math
        meshprops = []
        imported_props = []
        imported_textures = []
        imported_objects = []
        material_object = None
        rootObject = rootObj
        material_type = 'default.xml'
        for group in root:
            if group.tag == 'material':
                material_type = group.text

        if rootObj is not None:
            print("Root object is:" + rootObj.name)

        for group in root:
            if group.tag == 'material':
                continue

            if len(group) == 0:
                continue

            variant = group[0]
            # If there is more than one group pick one randomly.
            if len(group) > 1:
                retries = 0
                while (('frequency' not in variant.attrib or variant.attrib['frequency'] == "0") and retries < len(group)):
                    variant = group[random.randint(0,len(group) - 1)]
                    retries = retries + 1

            if 'file' in variant.attrib:
                present_tags = [child.tag for child in variant]

                variantParent = ET.parse(self.currentPath + 'variants/' +  variant.attrib['file']).getroot()
                if 'mesh' not in present_tags:
                    mesh_child = self.get_mesh_from_variant(variantParent)
                    if mesh_child is not None:
                        variant.append(mesh_child)

                variant_parent_textures = self.get_textures_from_variant(variantParent)
                if 'textures' not in present_tags:
                    if variant_parent_textures is not None:
                        variant.append(variant_parent_textures)
                elif variant_parent_textures is not None:
                    variant_tags = [texture.attrib['name'] for texture in variant.find('textures')]
                    for texture in variant_parent_textures:
                        if texture is not None and texture.attrib['name'] not in variant_tags:
                            variant.find('textures').append(texture)

                variant_parent_props = self.get_props_from_variant(variant)
                if 'props' not in present_tags and variant_parent_props is not None:
                    variant.append(variant_parent_props)
                elif variant_parent_props is not None:
                    variant_tags = [prop.attrib['attachpoint'] for prop in variant.find('props')]
                    for prop in variant_parent_props:
                        if prop is not None and prop.attrib['attachpoint'] not in variant_tags:
                            variant.find('props').append(prop)

            for child in variant:
                if(child.tag == 'mesh' or child.tag == 'decal'):
                    print("=======================================================")
                    print("============== Gathering Mesh =========================")
                    print("=======================================================")

                    # Get the objects prior to importing
                    prior_objects = [Object for Object in bpy.context.scene.objects]
                    prior_materials = [material for material in bpy.data.materials]
                    # Deselect all the previously selected objects.
                    for obj in prior_objects:
                        obj.select_set(False)
                    # Import the new objects
                    if child.tag == "mesh":
                        mesh_path = self.currentPath + 'meshes/' + child.text
                        try:

                            fixer = MaxColladaFixer(mesh_path)
                            fixer.execute()
                            bpy.ops.wm.collada_import(filepath=mesh_path, import_units=True)
                        except Exception:
                            print('Could not load' + mesh_path)
                    else:
                        bpy.ops.object.select_all(action='DESELECT')
                        if material_type == 'default.xml' or 'terrain' in material_type:
                            material_type = 'basic_trans.xml'

                        decal = self.create_custom_mesh("Decal", float(child.attrib['offsetx']), float(child.attrib['offsetz']), 0, float(child.attrib['width']), float(child.attrib['depth']))
                        decal.select_set(True)
                        bpy.context.view_layer.objects.active = decal
                        bpy.ops.object.mode_set(mode='EDIT')
                        bpy.ops.uv.reset()
                        bpy.ops.object.mode_set(mode='OBJECT')
                        decal.rotation_euler = (0,0, math.radians(float(child.attrib['angle'])))

                    new_current_objects = [object for object in bpy.context.scene.objects]
                    # Select those objects
                    for obj in (set(new_current_objects) - set(prior_objects)):
                        obj.select_set(True)

                    backup =  bpy.context.selected_objects.copy()
                    for b in backup :
                        if b.data is None or b.data.uv_layers is None or not len(b.data.uv_layers):
                            continue
                        if len(b.data.uv_layers) > 0:
                            print("Renaming" + b.data.uv_layers[0].name + " to " + "UVMap")
                            b.data.uv_layers[0].name = "UVMap"

                        if len(b.data.uv_layers) > 1:
                            print("Renaming" + b.data.uv_layers[1].name + " to " + "AOMap")
                            b.data.uv_layers[1].name = "AOMap"


                    # Get those objects
                    imported_objects = bpy.context.selected_objects.copy()


                    for imported_object in imported_objects:
                        if imported_object is not None and 'prop.' in imported_object.name:
                            imported_object.name = imported_object.name.replace("prop.","prop_")
                            if imported_object.data is not None and 'prop.' in imported_object.data.name:
                                imported_object.data.name = imported_object.data.name.replace("prop.","prop_")
                        # props are parented so they should follow their root object.
                        if "prop-" in imported_object.name:
                            imported_object.name = imported_object.name.replace("prop-","prop_")
                            if imported_object.data is not None and 'prop-' in imported_object.data.name:
                                imported_object.data.name = imported_object.data.name.replace("prop-","prop_")
                        if "prop_" in imported_object.name:
                            meshprops.append(imported_object)
                            imported_object.select_set(False)

                    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

                    for obj in backup:
                        obj.select_set(True)
                    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

                    # Clear old materials
                    for ob in bpy.context.selected_editable_objects:
                        ob.active_material_index = 0
                        for i in range(len(ob.material_slots)):
                            bpy.ops.object.material_slot_remove()

                    new_current_materials = [material for material in bpy.data.materials]
                    for material in (set(new_current_materials) - set(prior_materials)):
                        bpy.data.materials.remove(material)
                    print("=======================================================")
                    print("============== Setting Constraints ====================")
                    print("=======================================================")

                    for imported_object in imported_objects:
                        # props are parented so they should follow their root object.
                        if ('prop-' in imported_object.name or 'prop_' in imported_object.name) and hasattr(imported_object, 'type') and imported_object.type == 'EMPTY':
                            continue

                        if proppoint == 'root' and rootObj is not None:
                            self.set_copy_transform_constraint(imported_object, rootObj)
                            continue

                        found = False
                        for prop in parentprops:
                            if proppoint in prop.name:
                                found = True
                                self.set_copy_transform_constraint(imported_object, prop)
                                break

                        if found:
                            continue

                        print('' + imported_object.name + ' has no parent prop point named prop_' + proppoint + '. Root object name: ' + (rootObj.name if rootObj is not None else 'Undefined')  + '')

                if(child.tag == 'textures' and self.import_textures):
                    print("=======================================================")
                    print("============== Gathering Textures =====================")
                    print("=======================================================")
                    if(len(child) > 0):
                        for texture in child:
                            imported_textures.append(texture)

                if(child.tag == 'props' and self.import_props and (self.import_depth == -1 or (self.import_depth > propDepth and self.import_depth > 0))):

                    print("=======================================================")
                    print("============== Gathering Parent Props =================")
                    print("=======================================================")

                    finalprops = imported_objects.copy()
                    if len(finalprops) > 0:
                        rootObject = None
                        for obj in finalprops:
                            if ('prop-' in obj.name or 'prop_' in obj.name):
                                continue

                            if hasattr(obj, 'type') and obj.type == 'ARMATURE':
                                print("=======================================================")
                                print("============== Gathering Armature Props ===============")
                                print("=======================================================")

                                for bone in obj.data.bones:
                                    if 'prop.' in bone.name:
                                        bone.name = bone.name.replace('prop.','prop_')
                                    if 'prop-' in bone.name:
                                        bone.name = bone.name.replace('prop-','prop_')
                                    if 'prop_' in bone.name:
                                        print(bone.name)
                                        finalprops.append(bone)

                                continue
                            if hasattr(obj, 'type'):
                                rootObject = bpy.data.objects[obj.name]
                            finalprops.remove(obj)

                    if rootObject is not None:
                        print(rootObject.name)

                    for prop in child:
                        imported_props.append(prop)

        mat_textures = []
        for texture in imported_textures:
            print("Loading " + texture.attrib['name'] + ": " + self.currentPath + 'textures/skins/' + texture.attrib['file'])
            bpy.data.images.load(self.currentPath + 'textures/skins/' + texture.attrib['file'], check_existing=True)
            mat_textures.append(texture.attrib['name'] + '|' + self.currentPath + 'textures/skins/' + texture.attrib['file'])

        if len(mat_textures):
            material_object = self.create_new_material(mat_textures, material_type)

            for obj in imported_objects:
                if ('prop-' in obj.name or 'prop_' in obj.name) and not hasattr(obj, 'type'):
                    continue
                if hasattr(obj, 'type') and obj.type == 'EMPTY':
                    continue
                if hasattr(obj, 'type') and obj.type == 'ARMATURE':
                    continue

                self.assign_material_to_object(obj, material_object)

        for prop in imported_props:
            print("=======================================================")
            print("============== Gathering Props ========================")
            print("=======================================================")
            if prop.attrib['actor'] == "":
                continue

            try:
                prop_path = self.currentPath + 'actors/' +  prop.attrib['actor']
                print('Loading ' + prop_path + '.')
                proproot = ET.parse(prop_path).getroot()

                propRootObj = self.find_prop_root_object(finalprops, prop.attrib['attachpoint'])
                if propRootObj is not None and prop.attrib['attachpoint'] != 'root' and rootObject is None:
                    rootObject = propRootObj

                self.parse_actor(proproot, prop.attrib['attachpoint'], meshprops if finalprops is None or len(finalprops) <= 0 else finalprops, rootObject, propDepth + 1)
            except Exception:
                print('Could not load' + mesh_path)


    def find_prop_root_object(self, imported_objects, proppoint):
        for imported_object in imported_objects:
            if 'prop_' + proppoint in imported_object.name:
                return imported_object

        return None
