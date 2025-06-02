name: Release

on:
  release:
    types: [created]

env:
  PYTHON_VERSION: "3.11"

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: release
    permissions:
      id-token: write  # IMPORTANT: this permission is mandatory for trusted publishing
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{{{ env.PYTHON_VERSION }}}}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Check package
      run: twine check dist/*
    
    - name: Publish to Test PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        repository-url: https://test.pypi.org/legacy/
        skip-existing: true
    
    - name: Test installation from Test PyPI
      run: |
        pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ {context.package_name}
        python -c "import {context.package_name}; print({context.package_name}.__version__)"
    
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
    
    - name: Create GitHub Release Assets
      run: |
        echo "Package published successfully!" > release_notes.txt
        echo "Version: ${{{{ github.event.release.tag_name }}}}" >> release_notes.txt
        echo "PyPI: https://pypi.org/project/{context.package_name}/" >> release_notes.txt
    
    - name: Upload Release Assets
      uses: actions/upload-release-asset@v1
      env:
        GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
      with:
        upload_url: ${{{{ github.event.release.upload_url }}}}
        asset_path: ./release_notes.txt
        asset_name: release_notes.txt
        asset_content_type: text/plain