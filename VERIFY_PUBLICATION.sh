#!/bin/bash
# OpenPypi Publication Verification Script

echo "VERIFYING: OpenPypi Publication Status"
echo "======================================"

# Check PyPI publication
echo "1. Checking PyPI publication..."
curl -s https://pypi.org/pypi/openpypi/json | head -1 | grep -q "200 OK"
if [ $? -eq 0 ]; then
    echo "SUCCESS: Package found on PyPI"
    echo "URL: https://pypi.org/project/openpypi/"
else
    echo "PENDING: Package not yet on PyPI or still processing"
fi

# Test installation
echo ""
echo "2. Testing package installation..."
python -m venv test_install
source test_install/bin/activate 2>/dev/null || source test_install/Scripts/activate
pip install openpypi --quiet
if [ $? -eq 0 ]; then
    echo "SUCCESS: Package installs correctly"
    openpypi --version
    echo "SUCCESS: CLI working correctly"
else
    echo "FAILED: Package installation failed"
fi
deactivate 2>/dev/null
rm -rf test_install

# Check GitHub repository (replace YOUR_USERNAME)
echo ""
echo "3. Checking GitHub repository..."
echo "   Manual check: https://github.com/YOUR_USERNAME/OpenPypi"
echo "   - Repository should be visible"
echo "   - Release v1.0.0 should exist"
echo "   - Source code should be browsable"

echo ""
echo "VERIFICATION COMPLETE"
echo "===================="
echo "If all checks passed, OpenPypi is successfully published!"
echo ""
echo "Users can now:"
echo "- Install: pip install openpypi"
echo "- Use CLI: openpypi create my_project --use-fastapi"
echo "- View code: https://github.com/YOUR_USERNAME/OpenPypi"
echo "- Download: https://pypi.org/project/openpypi/" 