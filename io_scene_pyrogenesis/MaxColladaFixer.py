# Copyright (C) 2024 Wildfire Games.
# This file is part of 0 A.D.
# SPDX-License-Identifier: GPL-2.0-or-later

import logging


class MaxColladaFixer:
    file_path = None
    collada_prefix = "{http://www.collada.org/2005/11/COLLADASchema}"

    def sortchildrenby(self, parent):
        parent[:] = sorted(parent, key=lambda child: child.tag)

    def indent(self, elem, level=0):
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def __init__(self, file_path=None):
        self.file_path = file_path
        self.logger = logging.getLogger("PyrogenesisActorImporter." % __name__)

    def execute(self):
        import xml.etree.ElementTree as ET
        from datetime import date

        tree = ET.parse(self.file_path)
        ET.register_namespace("", "http://www.collada.org/2005/11/COLLADASchema")
        root = tree.getroot()
        new_elements = []
        for child in root:
            self.logger.info("Fixing Collada..." + child.tag)
        for child in root[:]:
            if child.tag == self.collada_prefix + "library_images":
                root.remove(child)
                element = ET.Element(self.collada_prefix + "library_images")
                new_elements.append(element)
                continue

            if child.tag == self.collada_prefix + "library_materials":
                root.remove(child)

                # If there is no material no need to append it.
                continue

            if child.tag == self.collada_prefix + "library_effects":
                root.remove(child)

                element = ET.Element(self.collada_prefix + "library_effects")
                new_elements.append(element)
                continue

            if child.tag == self.collada_prefix + "library_visual_scenes":
                for visual_scene in child:
                    for node in visual_scene:
                        for subchild in node:
                            if (
                                subchild.tag
                                == self.collada_prefix + "instance_geometry"
                            ):
                                for binding in subchild:
                                    if (
                                        binding.tag
                                        == self.collada_prefix + "bind_material"
                                    ):
                                        subchild.remove(binding)
                                        break
                            if (
                                subchild.tag
                                == self.collada_prefix + "instance_controller"
                            ):
                                for binding in subchild:
                                    if (
                                        binding.tag
                                        == self.collada_prefix + "bind_material"
                                    ):
                                        subchild.remove(binding)
                                        break
                continue

            if child.tag == self.collada_prefix + "asset":
                for property in child:
                    if property.tag == self.collada_prefix + "modified":
                        property.text = str(date.today())

        for element in new_elements:
            root.append(element)

        self.sortchildrenby(root)
        for child in root:
            self.sortchildrenby(child)
        self.indent(root)
        tree.write(open(self.file_path, "wb"), encoding="utf-8")
        tree.write(open(self.file_path, "wb"), encoding="utf-8")
