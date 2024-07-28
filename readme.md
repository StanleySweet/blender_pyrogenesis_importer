# Blender Pyrogenesis Importer

Blender extension to import models from the game 0ad using pyrogenesis

> [!NOTE]
> For Blender versions before 4.2 use the legacy add-on with version 1.x

## Build

```sh
python3 build.py
```

Alternatively using Blender 4.2+

```sh
cd io_scene_pyrogenesis
blender --command extension build
```

## Installation

1. Build or download the latest release of io_scene_pyrogenesis.zip
2. In Blender, navigate to **Edit > Preferences... > Get Extensions** and in the dropdown menu in the top right corner select **Install from Disk...**

You can now import pyrogenesis xml actor files with **File > Import > Pyrogenesis Actor (.xml)**.

## Unsupported Features

- Animation Import
- 3Dsmax Animation Import
- Multiple armatures with the same name
