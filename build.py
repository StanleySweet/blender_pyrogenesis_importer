# Copyright (C) 2023 Wildfire Games.
# This file is part of 0 A.D.
# SPDX-License-Identifier: GPL-2.0-or-later

import os
try: 
    import tomllib
except ModuleNotFoundError: 
    import pip._vendor.tomli as tomllib

import zipfile


def get_version():
    with open("io_scene_pyrogenesis/blender_manifest.toml", "rb") as f:
        manifest = tomllib.load(f)
        return manifest["version"]


def build_archive():
    os.makedirs("dist", exist_ok=True)
    with zipfile.ZipFile(os.path.join("dist", "io_scene_pyrogenesis-" + get_version() + ".zip"), mode="w") as archive:
        archive.write("io_scene_pyrogenesis/__init__.py")
        archive.write("io_scene_pyrogenesis/blender_manifest.toml")
        archive.write("LICENSE", arcname="io_scene_pyrogenesis/LICENSE")


if __name__ == '__main__':
    build_archive()
