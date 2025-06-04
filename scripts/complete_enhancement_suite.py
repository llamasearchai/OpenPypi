#!/usr/bin/env python3
"""
Complete Enhancement Suite for OpenPypi
Automates testing, building, and ensures everything works perfectly.
"""

import os
import sys
import subprocess
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import asyncio

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhancement_suite.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancementSuite:
    """Complete enhancement suite for OpenPypi."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.results = {}
        
    def run_command(self, command: str, description: str) -> Dict[str, Any]:
        """Run a command and return results."""
        logger.info(f"Running: {description}")
        logger.info(f"Command: {command}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=300  # 5 minute timeout
            )
            end_time = time.time()
            
            success = result.returncode == 0
            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "duration": end_time - start_time,
                "command": command,
                "description": description
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timed out",
                "returncode": -1,
                "duration": time.time() - start_time,
                "command": command,
                "description": description
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "duration": time.time() - start_time,
                "command": command,
                "description": description
            }
    
    def check_environment(self) -> bool:
        """Check that the environment is properly set up."""
        logger.info("🔍 Checking environment setup...")
        
        checks = [
            ("python --version", "Python version check"),
            ("pip --version", "Pip version check"),
            ("which pytest", "Pytest availability"),
            ("ls src/openpypi", "Source directory check"),
            ("ls tests", "Tests directory check")
        ]
        
        all_passed = True
        for command, description in checks:
            result = self.run_command(command, description)
            if not result["success"]:
                logger.error(f"❌ {description} failed")
                all_passed = False
            else:
                logger.info(f"✅ {description} passed")
        
        return all_passed
    
    def install_dependencies(self) -> bool:
        """Install all dependencies."""
        logger.info("📦 Installing dependencies...")
        
        commands = [
            ("pip install -e .", "Install package in development mode"),
            ("pip install -r requirements-dev.txt", "Install development dependencies"),
            ("pip install pytest pytest-cov pytest-asyncio", "Install testing dependencies")
        ]
        
        for command, description in commands:
            result = self.run_command(command, description)
            if not result["success"]:
                logger.error(f"❌ {description} failed: {result['stderr']}")
                return False
            else:
                logger.info(f"✅ {description} completed")
        
        return True
    
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite."""
        logger.info("🧪 Running comprehensive test suite...")
        
        # Run all tests with coverage
        test_result = self.run_command(
            "python -m pytest tests/ --cov=src/openpypi --cov-report=term --cov-report=html --cov-report=xml -v --tb=short",
            "Complete test suite with coverage"
        )
        
        # Parse coverage from output
        coverage_percentage = self.extract_coverage_percentage(test_result["stdout"])
        
        # Run specific test files
        specific_tests = [
            "tests/complete_system_tests.py",
            "tests/comprehensive_coverage_booster.py",
            "tests/targeted_coverage_booster.py"
        ]
        
        test_results = {"main_test": test_result, "coverage": coverage_percentage}
        
        for test_file in specific_tests:
            if os.path.exists(test_file):
                result = self.run_command(
                    f"python -m pytest {test_file} -v",
                    f"Running {test_file}"
                )
                test_results[test_file] = result
        
        return test_results
    
    def extract_coverage_percentage(self, output: str) -> float:
        """Extract coverage percentage from pytest output."""
        try:
            for line in output.split('\n'):
                if 'TOTAL' in line and '%' in line:
                    parts = line.split()
                    for part in parts:
                        if '%' in part:
                            return float(part.replace('%', ''))
            return 0.0
        except:
            return 0.0
    
    def lint_code(self) -> Dict[str, Any]:
        """Run code linting."""
        logger.info("🔍 Running code linting...")
        
        linting_commands = [
            ("python -m flake8 src/openpypi --max-line-length=100 --ignore=E203,W503", "Flake8 linting"),
            ("python -m black --check src/openpypi", "Black formatting check"),
            ("python -m isort --check-only src/openpypi", "Import sorting check")
        ]
        
        results = {}
        for command, description in linting_commands:
            result = self.run_command(command, description)
            results[description] = result
            if result["success"]:
                logger.info(f"✅ {description} passed")
            else:
                logger.warning(f"⚠️ {description} has issues")
        
        return results
    
    def run_security_checks(self) -> Dict[str, Any]:
        """Run security checks."""
        logger.info("🔒 Running security checks...")
        
        security_commands = [
            ("python -m bandit -r src/openpypi", "Bandit security scan"),
            ("python -m safety check", "Safety dependency check")
        ]
        
        results = {}
        for command, description in security_commands:
            result = self.run_command(command, description)
            results[description] = result
            if result["success"]:
                logger.info(f"✅ {description} passed")
            else:
                logger.warning(f"⚠️ {description} found issues")
        
        return results
    
    def build_documentation(self) -> bool:
        """Build project documentation."""
        logger.info("📚 Building documentation...")
        
        doc_commands = [
            ("python -c \"import src.openpypi; print('Import successful')\"", "Test import"),
            ("python -m pydoc src.openpypi", "Generate basic docs")
        ]
        
        for command, description in doc_commands:
            result = self.run_command(command, description)
            if not result["success"]:
                logger.error(f"❌ {description} failed")
                return False
            else:
                logger.info(f"✅ {description} completed")
        
        return True
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        logger.info("⚡ Running performance tests...")
        
        perf_results = {}
        
        # Test import time
        import_test = self.run_command(
            "python -c \"import time; start=time.time(); import src.openpypi; print(f'Import time: {time.time()-start:.3f}s')\"",
            "Import performance test"
        )
        perf_results["import_time"] = import_test
        
        # Test basic functionality
        basic_test = self.run_command(
            "python -c \"from src.openpypi.api.app import app; print('App creation successful')\"",
            "Basic functionality test"
        )
        perf_results["basic_functionality"] = basic_test
        
        return perf_results
    
    def create_health_report(self) -> Dict[str, Any]:
        """Create a comprehensive health report."""
        logger.info("📊 Creating health report...")
        
        health_report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "project_root": str(self.project_root),
            "python_version": sys.version,
            "tests": {},
            "linting": {},
            "security": {},
            "performance": {},
            "overall_status": "unknown"
        }
        
        # Run all checks
        try:
            health_report["tests"] = self.run_comprehensive_tests()
            health_report["linting"] = self.lint_code()
            health_report["security"] = self.run_security_checks()
            health_report["performance"] = self.run_performance_tests()
            
            # Determine overall status
            test_success = health_report["tests"]["main_test"]["success"]
            coverage = health_report["tests"]["coverage"]
            
            if test_success and coverage >= 95:
                health_report["overall_status"] = "excellent"
            elif test_success and coverage >= 80:
                health_report["overall_status"] = "good"
            elif test_success:
                health_report["overall_status"] = "fair"
            else:
                health_report["overall_status"] = "needs_improvement"
                
        except Exception as e:
            logger.error(f"Error creating health report: {e}")
            health_report["error"] = str(e)
            health_report["overall_status"] = "error"
        
        return health_report
    
    def fix_common_issues(self) -> bool:
        """Attempt to fix common issues automatically."""
        logger.info("🔧 Attempting to fix common issues...")
        
        fixes = [
            ("python -m black src/openpypi", "Auto-format code with Black"),
            ("python -m isort src/openpypi", "Sort imports"),
            ("find . -name '*.pyc' -delete", "Remove Python cache files"),
            ("find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true", "Remove cache directories")
        ]
        
        for command, description in fixes:
            result = self.run_command(command, description)
            if result["success"]:
                logger.info(f"✅ {description} completed")
            else:
                logger.warning(f"⚠️ {description} failed: {result['stderr']}")
        
        return True
    
    def generate_summary_report(self, health_report: Dict[str, Any]) -> str:
        """Generate a summary report."""
        summary = []
        summary.append("=" * 60)
        summary.append("OpenPypi Enhancement Suite - Summary Report")
        summary.append("=" * 60)
        summary.append(f"Timestamp: {health_report['timestamp']}")
        summary.append(f"Overall Status: {health_report['overall_status'].upper()}")
        summary.append("")
        
        # Test results
        if "tests" in health_report:
            tests = health_report["tests"]
            summary.append("📊 TEST RESULTS:")
            summary.append(f"  Main Test Suite: {'✅ PASSED' if tests['main_test']['success'] else '❌ FAILED'}")
            summary.append(f"  Test Coverage: {tests['coverage']:.1f}%")
            summary.append("")
        
        # Coverage target
        coverage = health_report.get("tests", {}).get("coverage", 0)
        if coverage >= 95:
            summary.append("🎯 COVERAGE TARGET: ✅ ACHIEVED (≥95%)")
        else:
            summary.append(f"🎯 COVERAGE TARGET: ❌ NOT MET ({coverage:.1f}% < 95%)")
        summary.append("")
        
        # Recommendations
        summary.append("💡 RECOMMENDATIONS:")
        if coverage < 95:
            summary.append("  - Add more comprehensive tests to reach 95% coverage")
        if health_report["overall_status"] != "excellent":
            summary.append("  - Review and fix any failing tests")
            summary.append("  - Address linting and security issues")
        summary.append("  - Run this suite regularly to maintain code quality")
        summary.append("")
        
        summary.append("=" * 60)
        return "\n".join(summary)
    
    def run_full_suite(self) -> bool:
        """Run the complete enhancement suite."""
        logger.info("🚀 Starting OpenPypi Complete Enhancement Suite")
        logger.info("=" * 60)
        
        try:
            # Step 1: Check environment
            if not self.check_environment():
                logger.error("❌ Environment check failed")
                return False
            
            # Step 2: Install dependencies
            if not self.install_dependencies():
                logger.error("❌ Dependency installation failed")
                return False
            
            # Step 3: Fix common issues
            self.fix_common_issues()
            
            # Step 4: Create health report
            health_report = self.create_health_report()
            
            # Step 5: Save detailed report
            report_file = "enhancement_suite_report.json"
            with open(report_file, 'w') as f:
                json.dump(health_report, f, indent=2)
            logger.info(f"📄 Detailed report saved to {report_file}")
            
            # Step 6: Generate and display summary
            summary = self.generate_summary_report(health_report)
            print("\n" + summary)
            
            # Step 7: Save summary
            summary_file = "enhancement_suite_summary.txt"
            with open(summary_file, 'w') as f:
                f.write(summary)
            logger.info(f"📄 Summary saved to {summary_file}")
            
            # Determine success
            success = health_report["overall_status"] in ["excellent", "good"]
            coverage_target_met = health_report.get("tests", {}).get("coverage", 0) >= 95
            
            if success and coverage_target_met:
                logger.info("🎉 Enhancement suite completed successfully!")
                logger.info("✅ All targets achieved!")
                return True
            else:
                logger.warning("⚠️ Enhancement suite completed with issues")
                logger.warning("❌ Some targets not met")
                return False
                
        except Exception as e:
            logger.error(f"💥 Enhancement suite failed: {e}")
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenPypi Complete Enhancement Suite")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--quick", action="store_true", help="Run quick checks only")
    
    args = parser.parse_args()
    
    suite = EnhancementSuite(args.project_root)
    
    if args.quick:
        # Quick mode - just run tests
        logger.info("🏃 Running in quick mode...")
        test_results = suite.run_comprehensive_tests()
        coverage = test_results.get("coverage", 0)
        success = test_results["main_test"]["success"]
        
        if success and coverage >= 95:
            print("✅ Quick check PASSED - Coverage target achieved!")
            sys.exit(0)
        else:
            print(f"❌ Quick check FAILED - Coverage: {coverage:.1f}%")
            sys.exit(1)
    else:
        # Full suite
        success = suite.run_full_suite()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 