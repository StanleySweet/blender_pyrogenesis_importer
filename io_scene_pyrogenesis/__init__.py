# Copyright (C) 2019 Wildfire Games.
# This file is part of 0 A.D.
#
# 0 A.D. is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# 0 A.D. is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with 0 A.D.  If not, see <http://www.gnu.org/licenses/>.
#

# 'https://blender.stackexchange.com/questions/39303/blender-script-import-model-and-render-it'


bl_info = {
    'name': 'Blender Pyrogenesis Importer',
    'author': 'Stanislas Daniel Claude Dolcini',
    'version': (1, 2, 0),
    'blender':  (2, 80, 0),
    'location': 'File > Import-Export',
    'description': 'Import ',
    'wiki_url': 'https://github.com/StanleySweet/blender_pyrogenesis_importer',
    'category': 'Import-Export'
}

def get_version_string():
    return str(bl_info['version'][0]) + '.' + str(bl_info['version'][1]) + '.' + str(bl_info['version'][2])


#
# Script reloading (if the user calls 'Reload Scripts' from Blender)
#

def reload_package(module_dict_main):
    import importlib
    from pathlib import Path

    def reload_package_recursive(current_dir, module_dict):
        for path in current_dir.iterdir():
            if "__init__" in str(path) or path.stem not in module_dict:
                continue

            if path.is_file() and path.suffix == ".py":
                importlib.reload(module_dict[path.stem])
            elif path.is_dir():
                reload_package_recursive(path, module_dict[path.stem].__dict__)

    reload_package_recursive(Path(__file__).parent, module_dict_main)

if "bpy" in locals():
    reload_package(locals())

import bpy
from bpy.props import (StringProperty,
                       BoolProperty,
                       EnumProperty,
                       IntProperty)
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper, ExportHelper


def menu_func_import(self, context):
    self.layout.operator(ImportPyrogenesisActor.bl_idname, text='Pyrogenesis Actor (.xml)')

def register():
    # bpy.utils.register_module(__name__)
    bpy.utils.register_class(ImportPyrogenesisActor)
    # add to the export / import menu
    if bpy.app.version < (2, 80, 0):
        bpy.types.INFO_MT_file_import.append(menu_func_import)
    else:
        bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    # bpy.utils.unregister_module(__name__)
    bpy.utils.unregister_class(ImportPyrogenesisActor)
    # remove from the export / import menu
    if bpy.app.version < (2, 80, 0):
        bpy.types.INFO_MT_file_import.remove(menu_func_import)
    else:
        bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

import os, sys

class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout

class ImportPyrogenesisActor(Operator, ImportHelper):
    """Load a Pyrogenesis actor file"""
    bl_label = "Import Pyrogenesis Actor"
    bl_idname = 'import_scene.xml'
    filter_glob = StringProperty(default="*.xml", options={'HIDDEN'})
    currentPath = ""

    import_props = BoolProperty(
        name='Import props',
        description='Whether to include props in the importation.',
        default=True
    )

    import_textures = BoolProperty(
        name='Import textures',
        description='Whether to include textures in the importation.',
        default=True
    )

    import_depth = IntProperty(
        name='Import Depth',
        description='How much prop depth there should be',
        default=-1
    )


    def draw(self, context):
        layout = self.layout

        layout.prop(self, 'import_props')
        layout.prop(self, 'import_textures')
        layout.prop(self, 'import_depth')

    def execute(self, context):
        return self.import_pyrogenesis_actor(context)

    def find_parent_armature(self, bone):

        for armature in bpy.data.armatures:
            for bone2 in armature.bones:
                if bone2.name == bone.name:
                    return bpy.data.objects[armature.name]

        return None


    def set_copy_transform_constraint(self, obj, parent):
        """Set constraints for props so that they fit their prop point."""
        print(obj.name + " -> " + parent.name)
        if(str(type(parent)) == '<class \'bpy_types.Bone\'>'):
            armature = self.find_parent_armature(parent)
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


        constraint = obj.constraints.new('COPY_LOCATION')
        constraint.show_expanded = False
        constraint.mute = False
        constraint.target = parent
        constraint2 = obj.constraints.new('COPY_ROTATION')
        constraint2.show_expanded = False
        constraint2.mute = False
        constraint2.target = parent
        obj.parent = parent

    def create_new_material(self, textures):
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
                # TODO: playercolor, alpha
                continue
            
            if texture.split('|')[0] == 'normTex':
                texImage.image.colorspace_settings.name='Non-Color'
                normal_node = mat.node_tree.nodes.new('ShaderNodeNormalMap')
                mat.node_tree.links.new(normal_node.inputs['Color'], texImage.outputs['Color'])                
                mat.node_tree.links.new(bsdf.inputs['Normal'], normal_node.outputs['Normal'])
                continue

            
            if texture.split('|')[0] == 'specTex':
                mat.node_tree.links.new(bsdf.inputs['Specular'], texImage.outputs['Color'])
                continue
            
         
            
            
            

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

        self.currentPath = (self.filepath[0:self.filepath.find('actors\\')]).replace("\\", "/")
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




        mymesh = bpy.data.meshes.new(objname)
        myobject = bpy.data.objects.new(objname, mymesh)

        scene = bpy.context.scene
        scene.collection.objects.link(myobject)
        # bpy.context.scene.objects.link(myobject)

        # Generate mesh data
        mymesh.from_pydata(myvertex, [], myfaces)
        # Calculate the edges
        mymesh.update(calc_edges=True)

        # Set Location
        myobject.location.x = px
        myobject.location.y = py
        myobject.location.z = pz
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



        # No mesh was found in this variant.


    def parse_actor(self, root, proppoint="root", parentprops=[], rootObj=None, propDepth=0):
        import xml.etree.ElementTree as ET
        import bpy
        import os
        import sys
        import random
        import math
        meshprops = []
        props = []
        textures = []
        material_object = None
        rootObject = None
        material = None
        for group in root:
            if group.tag == 'material':
                material = group.text

        imported_objects = []
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
                            variant['textures'].append(texture)

                variant_parent_props = self.get_props_from_variant(variant)
                if 'props' not in present_tags and variant_parent_props is not None:
                    variant.append(variant_parent_props)
                elif variant_parent_props is not None:
                    variant_tags = [prop.attrib['attachpoint'] for prop in variant.find('props')]
                    for prop in variant_parent_props:
                        if prop is not None and prop.attrib['attachpoint'] not in variant_tags:
                            variant['props'].append(prop)
                    
                    
                    
                    


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
                        with HiddenPrints():
                            fixer = MaxColladaFixer(self.currentPath + 'meshes/' + child.text)
                            fixer.execute()
                            bpy.ops.wm.collada_import(filepath=(self.currentPath + 'meshes/' + child.text), import_units=True)
                    else:
                        bpy.ops.object.select_all(action='DESELECT')
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
                    # Get those objects
                    imported_objects = bpy.context.selected_objects.copy()


                    for imported_object in imported_objects:
                        # props are parented so they should follow their root object.
                        if "prop-" in imported_object.name or "prop_" in imported_object.name:
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

                        if found == True:
                            continue

                        print('\033[93m' + imported_object.name + " has no parent prop point named prop-" + proppoint + '\033[0m')

                if(child.tag == 'textures' and self.import_textures):
                    print("=======================================================")
                    print("============== Gathering Textures =====================")
                    print("=======================================================")
                    if(len(child) > 0):
                        for texture in child:
                            textures.append(texture)



                if(child.tag == 'props' and self.import_props and (self.import_depth == -1 or (self.import_depth > propDepth and self.import_depth > 0))):

                    print("=======================================================")
                    print("============== Gathering Parent Props =================")
                    print("=======================================================")

                    finalprops = imported_objects.copy()

                    if len(finalprops) > 0:
                        for obj in finalprops:
                            if ('prop-' in obj.name or 'prop_' in obj.name):
                                continue

                            if hasattr(obj, 'type') and obj.type == 'ARMATURE':
                                for bone in obj.data.bones:
                                    if "prop-" in bone.name or "prop_" in bone.name:
                                        finalprops.append(bone)
                                continue

                            if hasattr(obj, 'type'):

                                rootObject = obj

                            finalprops.remove(obj)



                    for prop in child:
                        props.append(prop)

        mat_textures = []
        for texture in textures:
            print("Loading " + texture.attrib['name'] + ": " + self.currentPath + 'textures/skins/' + texture.attrib['file'])
            bpy.data.images.load(self.currentPath + 'textures/skins/' + texture.attrib['file'], check_existing=True)
            mat_textures.append(texture.attrib['name'] + '|' + self.currentPath + 'textures/skins/' + texture.attrib['file'])
        
        if len(mat_textures):
            material_object = self.create_new_material(mat_textures)

            for obj in imported_objects:
                if ('prop-' in obj.name or 'prop_' in obj.name) and not hasattr(obj, 'type'):
                    continue
                if hasattr(obj, 'type') and obj.type == 'EMPTY':
                    continue
                if hasattr(obj, 'type') and obj.type == 'ARMATURE':
                    continue

                self.assign_material_to_object(obj, material_object)

        for prop in props:
            print("=======================================================")
            print("============== Gathering Props ========================")
            print("=======================================================")
            print('Loading ' + self.currentPath + 'actors/' +  prop.attrib['actor'] + '.')
            proproot = ET.parse(self.currentPath + 'actors/' +  prop.attrib['actor']).getroot()
            if finalprops is None or len(finalprops) <= 0:
                self.parse_actor(proproot, prop.attrib['attachpoint'], meshprops, rootObject, propDepth + 1)
            else:
                self.parse_actor(proproot, prop.attrib['attachpoint'], finalprops, rootObject, propDepth + 1)

class MaxColladaFixer:
    file_path = None
    collada_prefix = '{http://www.collada.org/2005/11/COLLADASchema}'
    
    def sortchildrenby(self, parent):
        parent[:] = sorted(parent, key=lambda child: child.tag)

    
    def indent(self, elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    def __init__(self, file_path=None):
        self.file_path = file_path

    def execute(self):
        import xml.etree.ElementTree as ET   
        from datetime import date
        
        tree = ET.parse(self.file_path)
        ET.register_namespace("", "http://www.collada.org/2005/11/COLLADASchema")
        root = tree.getroot()
        new_elements = []
        
        for child in root:
            if child.tag == self.collada_prefix + 'library_images':
                root.remove(child)
                element = ET.Element(self.collada_prefix + 'library_images')
                new_elements.append(element)
                continue
                
            if child.tag == self.collada_prefix + 'library_materials':
                root.remove(child)
                
                element = ET.Element(self.collada_prefix + 'library_materials')
                new_elements.append(element)
                continue

            if child.tag == self.collada_prefix + 'library_effects':
                root.remove(child)
                
                element = ET.Element(self.collada_prefix + 'library_effects')
                new_elements.append(element)
                continue
                
            if child.tag == self.collada_prefix + 'asset':
                for property in child:
                    if property.tag == self.collada_prefix + 'modified':
                        property.text = str(date.today())
        
        
        for element in new_elements:
            root.append(element)

        self.indent(root)
        self.sortchildrenby(root)
        for child in root:
            self.sortchildrenby(child)
        tree.write(open(self.file_path, 'wb'), encoding='utf-8')
        tree.write(open(self.file_path, 'wb'),encoding='utf-8')


if __name__ == '__main__':
    register()
