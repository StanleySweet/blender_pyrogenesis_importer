# Copyright (C) 2024 Wildfire Games.
# This file is part of 0 A.D.
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from .import_pyrogenesis_actor import ImportPyrogenesisActor


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


def menu_func_import(self, context):
    self.layout.operator(
        ImportPyrogenesisActor.bl_idname, text="Pyrogenesis Actor (.xml)"
    )


def register():
    bpy.utils.register_class(ImportPyrogenesisActor)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportPyrogenesisActor)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
