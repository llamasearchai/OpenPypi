#!/usr/bin/env python3
"""
OpenPypi Complete Verification Script

This script verifies that all core functionality of OpenPypi is working correctly.
It tests project generation, FastAPI integration, OpenAI integration, and more.
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Dict, List

def test_basic_imports():
    """Test that all core modules can be imported."""
    print("Testing basic imports...")
    
    try:
        from openpypi.core import Config, ProjectGenerator
        from openpypi.core.context import Context
        from openpypi.core.orchestrator import Orchestrator
        from openpypi.providers import get_provider_registry
        from openpypi.stages import Stage, Pipeline
        from openpypi.utils.logger import get_logger
        print("  SUCCESS: All core imports work")
        return True
    except Exception as e:
        print(f"  FAILED: Import error - {e}")
        return False

def test_project_generation():
    """Test basic project generation."""
    print("Testing project generation...")
    
    try:
        from openpypi.core.config import Config
        from openpypi.core.generator import ProjectGenerator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                project_name="test-project",
                package_name="test_package",
                author="Test Author",
                email="test@example.com",
                output_dir=tmpdir,
                use_fastapi=True,
                use_docker=True
            )
            
            generator = ProjectGenerator(config)
            result = generator.generate()
            
            project_dir = Path(tmpdir) / "test-project"
            if project_dir.exists():
                files_created = len([f for f in project_dir.rglob("*") if f.is_file()])
                print(f"  SUCCESS: Generated project with {files_created} files")
                return True
            else:
                print("  FAILED: Project directory not created")
                return False
                
    except Exception as e:
        print(f"  FAILED: {e}")
        traceback.print_exc()
        return False

def test_fastapi_app():
    """Test FastAPI application setup."""
    print("Testing FastAPI application...")
    
    try:
        from openpypi.api.app import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        if response.status_code == 200:
            print("  SUCCESS: FastAPI app responds to health check")
            return True
        else:
            print(f"  FAILED: Health check returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

def test_providers():
    """Test provider system."""
    print("Testing provider system...")
    
    try:
        from openpypi.providers import get_provider_registry
        
        registry = get_provider_registry()
        providers = registry.list_providers()
        
        if len(providers) > 0:
            print(f"  SUCCESS: Found {len(providers)} providers: {', '.join(providers)}")
            return True
        else:
            print("  FAILED: No providers found")
            return False
            
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

def test_cli_interface():
    """Test CLI interface."""
    print("Testing CLI interface...")
    
    try:
        from openpypi.cli import main
        print("  SUCCESS: CLI module imports correctly")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

def test_security_features():
    """Test security features."""
    print("Testing security features...")
    
    try:
        from openpypi.core.security import (
            generate_api_key,
            get_password_hash,
            verify_password,
            create_access_token,
            decode_access_token
        )
        
        # Test password hashing
        password = "test_password"
        hashed = get_password_hash(password)
        if verify_password(password, hashed):
            print("  SUCCESS: Password hashing works")
        else:
            print("  FAILED: Password verification failed")
            return False
            
        # Test API key generation
        api_key = generate_api_key()
        if len(api_key) > 20:
            print("  SUCCESS: API key generation works")
        else:
            print("  FAILED: API key too short")
            return False
            
        # Test JWT tokens
        token_data = {"sub": "test_user"}
        token = create_access_token(token_data)
        decoded = decode_access_token(token)
        if decoded.get("sub") == "test_user":
            print("  SUCCESS: JWT token creation and verification works")
        else:
            print("  FAILED: JWT token verification failed")
            return False
            
        return True
        
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

def test_database_models():
    """Test database models."""
    print("Testing database models...")
    
    try:
        from openpypi.database.models import User, Project, Package, ApiKey, AuditLog
        print("  SUCCESS: Database models import correctly")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

def test_openai_integration():
    """Test OpenAI integration."""
    print("Testing OpenAI integration...")
    
    try:
        from openpypi.providers.ai import AIProvider
        from openpypi.providers.openai_provider import OpenAIProvider
        
        # Test provider instantiation
        ai_provider = AIProvider()
        print("  SUCCESS: OpenAI providers import correctly")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

def run_all_tests():
    """Run all verification tests."""
    print("OpenPypi Complete Verification")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_project_generation,
        test_fastapi_app,
        test_providers,
        test_cli_interface,
        test_security_features,
        test_database_models,
        test_openai_integration,
    ]
    
    results = {}
    
    for test in tests:
        test_name = test.__name__
        try:
            results[test_name] = test()
        except Exception as e:
            print(f"  CRITICAL: {test_name} crashed - {e}")
            results[test_name] = False
        print()
    
    # Summary
    print("VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\nSUCCESS: All verification tests passed! OpenPypi is ready for use.")
        return True
    else:
        print(f"\nWARNING: {total - passed} test(s) failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 