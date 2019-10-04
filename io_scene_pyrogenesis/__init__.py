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
    'version': (1, 0, 0),
    'blender':  (2, 80, 0),
    'location': 'File > Import-Export',
    'description': 'Import ',
    'wiki_url': 'https://wiki.blender.org/index.php/Extensions:2.6/Py/'
                'Scripts/Add_Mesh/BoltFactory',
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

    def draw(self, context):
        layout = self.layout

        layout.prop(self, 'import_props')

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
        import os
        mname = os.path.basename(textures[0])
        mat = bpy.data.materials.get(mname) or bpy.data.materials.new(name= mname)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = mat.node_tree.nodes["Principled BSDF"]


        for texture in textures:
            fname = os.path.basename(texture)
            texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
            texImage.image = bpy.data.images[fname]
            mat.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
            break

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
        import bpy
        import xml.etree.ElementTree as ET
        print('loading ' + self.filepath + '...')

        self.currentPath = (self.filepath[0:self.filepath.find('actors\\')]).replace("\\", "/")
        root = ET.parse(self.filepath).getroot()
        self.parse_actor(root)



        return {'FINISHED'}
    def create_custom_mesh(self, objname, px, py, pz):

        # Define arrays for holding data
        myvertex = []
        myfaces = []

        # Create all Vertices

        # vertex 0
        mypoint = [(-10.0, -10.0, 0.0)]
        myvertex.extend(mypoint)

        # vertex 1
        mypoint = [(10.0, -10.0, 0.0)]
        myvertex.extend(mypoint)

        # vertex 2
        mypoint = [(-10.0, 10.0, 0.0)]
        myvertex.extend(mypoint)

        # vertex 3
        mypoint = [(10.0, 10.0, 0.0)]
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
    def get_mesh_from_variant(self, root):
        import xml.etree.ElementTree as ET
        for child in root:
            if child.tag == 'mesh':
                return child

        # No mesh was found in this variant.
        if 'file' in root.attrib is not None:
            variantParent = ET.parse(self.currentPath + 'variants/' +  root.attrib['file']).getroot()
            return self.get_mesh_from_variant(variantParent)

        return None
    def parse_actor(self, root, proppoint="root", parentprops=[], rootObj=None):
        import xml.etree.ElementTree as ET
        from mathutils import Euler
        import bpy
        import os
        import sys
        import random
        from mathutils import Matrix
        import math

        material = None

        meshprops = []
        for group in root:
            if group.tag == 'material':
                material = group.text
                print(material)

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



            imported_objects = []

            for child in variant:
                if(child.tag == 'mesh' or child.tag == 'decal'):
                    print("=======================================================")
                    print("============== Gathering Mesh =========================")
                    print("=======================================================")

                    # Get the objects prior to importing
                    prior_objects = [object for object in bpy.context.scene.objects]
                    prior_materials = [material for material in bpy.data.materials]
                    # Deselect all the previously selected objects.
                    for obj in prior_objects:
                        obj.select_set(False)
                    # Import the new objects
                    if child.tag == "mesh":
                        with HiddenPrints():
                            bpy.ops.wm.collada_import(filepath=(self.currentPath + 'meshes/' + child.text), import_units=True)
                    else:
                        bpy.ops.object.select_all(action='DESELECT')
                        decal = self.create_custom_mesh("Decal", 0, 0, 0)
                        decal.select_set(True)
                        bpy.context.view_layer.objects.active = decal
                        bpy.ops.object.mode_set(mode='EDIT')
                        bpy.ops.uv.unwrap()
                        bpy.ops.object.mode_set(mode='OBJECT')
                        decal.rotation_euler = (0,0,1.5708)

                    new_current_objects = [object for object in bpy.context.scene.objects]
                    # Select those objects
                    for obj in (set(new_current_objects) - set(prior_objects)):
                        obj.select_set(True)

                    backup =  bpy.context.selected_objects.copy()
                    # Get those objects
                    imported_objects = bpy.context.selected_objects.copy()


                    for imported_object in imported_objects:
                        # print(imported_object.name)
                        # props are parented so they should follow their root object.
                        if "prop-" in imported_object.name or "prop_" in imported_object.name:
                            meshprops.append(imported_object)
                            imported_object.select_set(False)

                    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

                    for obj in backup:
                        obj.select_set(True)

                    # Clear old materials
                    for ob in bpy.context.selected_editable_objects:
                        ob.active_material_index = 0
                        for i in range(len(ob.material_slots)):
                            print("removing: " + ob.material_slots[0].name)
                            bpy.ops.object.material_slot_remove()

                    new_current_materials = [material for material in bpy.data.materials]
                    for material in (set(new_current_materials) - set(prior_materials)):
                        print("deleting: " + material.name)
                        bpy.data.materials.remove(material)
                    print("=======================================================")
                    print("============== Setting Constraints ====================")
                    print("=======================================================")
                    if proppoint == "root" and rootObj is not None:
                        for imported_object in imported_objects:
                            # props are parented so they should follow their root object.
                            if "prop-" in imported_object.name or "prop_" in imported_object.name:
                                continue
                            self.set_copy_transform_constraint(imported_object, rootObj)
                    else:
                        for imported_object in imported_objects:
                            # props are parented so they should follow their root object.
                            if "prop-" in imported_object.name or "prop_" in imported_object.name:
                                continue

                            for prop in parentprops:
                                if proppoint in prop.name:
                                    self.set_copy_transform_constraint(imported_object, prop)
                                    break

                            if proppoint == root:
                                self.set_copy_transform_constraint(imported_object, rootObj)
                            else:
                                print(imported_object.name + " has no parent prop point named prop-" + proppoint)

                if(child.tag == 'textures'):
                    print("=======================================================")
                    print("============== Gathering Textures =====================")
                    print("=======================================================")


                    for texture in child:
                        print("Loading " + texture.attrib['name'] + ": " + self.currentPath + 'textures/skins/' + texture.attrib['file'])
                        bpy.data.images.load(self.currentPath + 'textures/skins/' + texture.attrib['file'], check_existing=True)


                    if(len(child) > 0):
                        mname = self.create_new_material([self.currentPath + 'textures/skins/' + texture.attrib['file'] for texture in child])

                        if len(imported_objects) > 0:
                            for obj in imported_objects:
                                if obj.type is not None and obj.type == 'EMPTY':
                                    continue
                                if obj.type is not None and obj.type == 'ARMATURE':
                                    continue
                                if obj is not None:
                                    self.assign_material_to_object(obj, mname)

                if(child.tag == 'props'):
                    rootObject = None
                    print("=======================================================")
                    print("============== Gathering Parent Props =================")
                    print("=======================================================")

                    if len(imported_objects) > 0:
                        for obj in imported_objects:

                            if obj.type is not None and obj.type == 'EMPTY':
                                continue

                            if obj.type is not None and obj.type == 'ARMATURE':
                                for bone in obj.data.bones:
                                    if "prop-" in bone.name or "prop_" in bone.name:
                                        imported_objects.append(bone)
                                continue

                            if obj.type is not None and obj.type != 'EMPTY':
                                rootObject = obj

                            imported_objects.remove(obj)


                    finalprops =  imported_objects.copy()

                    for prop in child:
                        print("=======================================================")
                        print("============== Gathering Props ========================")
                        print("=======================================================")
                        proproot = ET.parse(self.currentPath + 'actors/' +  prop.attrib['actor']).getroot()
                        if finalprops is None or len(finalprops) <= 0:
                            self.parse_actor(proproot, prop.attrib['attachpoint'], meshprops, rootObject)
                        else:
                            self.parse_actor(proproot, prop.attrib['attachpoint'], finalprops, rootObject)



if __name__ == '__main__':
    register()