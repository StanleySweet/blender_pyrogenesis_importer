# Blender Pyrogenesis Importer Specification.

## Description

This importer will allow one to import an actor file with all the materials and all the dependencies. The goal is to then be able to export the model directly into other software like Godot, or Sketchfab, or as GLTF.

## Features

 - Importing actors.
 - Importing props and sub props
 - Importing textures.
 - Importing decals as planes. *
 - Importing Collada (*.dae) static meshes.
 - Importing Collada (*.dae) animated meshes. *
 - Creating materials. *

*: Feature not yet implemented.

## Usage

Given an actor XML file, the importer will be able to create a whole scene in Blender with no user intervention.
