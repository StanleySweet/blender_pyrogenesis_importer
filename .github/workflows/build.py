name: Build Archive

on:
  push:
    tags:
      - '*'

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout repository
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.x'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        python -c "import sys; print(sys.version_info[:2])" | grep -E '^\(3, (1[1-9]|[2-9][0-9])\)$' || python -m pip install tomli

    - name: Run build script
      run: python build.py

    - name: Upload artifact
      uses: actions/upload-artifact@v3
      with:
        name: io_scene_pyrogenesis
        path: dist/*
