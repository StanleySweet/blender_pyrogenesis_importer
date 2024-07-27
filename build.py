# Copyright (C) 2023 Wildfire Games.
# This file is part of 0 A.D.
# SPDX-License-Identifier: GPL-2.0-or-later

import ast, os, zipfile

def get_version():
    with open("io_scene_pyrogenesis/__init__.py", "r", encoding='UTF-8') as f:
        data = f.read()

    ast_data = ast.parse(data)
    for node in ast_data.body:
        if node.__class__ == ast.Assign:
            if len(node.targets) == 1:
                if getattr(node.targets[0], "id", "") == "bl_info":
                    break
    version = ast.literal_eval(node.value)["version"]
    return str(version[0]) + '.' + str(version[1]) + '.' + str(version[2])

def build_archive():
    os.makedirs("dist", exist_ok=True)
    with zipfile.ZipFile(os.path.join("dist", "io_scene_pyrogenesis-" + get_version() + ".zip"), mode="w") as archive:
        archive.write("io_scene_pyrogenesis/__init__.py")
        archive.write("LICENSE", arcname="io_scene_pyrogenesis/LICENSE")

if __name__ == '__main__':
    build_archive()
