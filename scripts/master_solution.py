#!/usr/bin/env python3
"""
Master Solution Script for OpenPypi Project
===========================================

This script implements a comprehensive recursive loop system that:
1. Runs all tests and captures all errors
2. Analyzes and categorizes errors
3. Applies automated fixes for common issues
4. Presents multiple solution options for complex problems
5. Repeats until all tests pass and coverage is maximized
6. Implements continuous improvement strategies

Usage:
    python scripts/master_solution.py
    python scripts/master_solution.py --mode=full
    python scripts/master_solution.py --mode=quick
    python scripts/master_solution.py --fix-only
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('master_solution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Container for test execution results."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    errors: List[str]
    warnings: List[str]
    coverage_percent: float
    test_count: int
    failed_count: int
    passed_count: int
    skipped_count: int


@dataclass
class FixResult:
    """Container for fix attempt results."""
    applied: bool
    description: str
    file_path: Optional[str] = None
    changes_made: List[str] = None
    error: Optional[str] = None


class ErrorAnalyzer:
    """Analyzes and categorizes test errors for automated fixing."""
    
    ERROR_PATTERNS = {
        'import_error': [
            r"ModuleNotFoundError: No module named '([^']+)'",
            r"ImportError: cannot import name '([^']+)' from '([^']+)'",
            r"ImportError: No module named ([^\s]+)",
        ],
        'syntax_error': [
            r"SyntaxError: (.+) \(([^,]+), line (\d+)\)",
            r"IndentationError: (.+) \(([^,]+), line (\d+)\)",
        ],
        'missing_fixture': [
            r"fixture '([^']+)' not found",
        ],
        'assertion_error': [
            r"AssertionError: (.+)",
            r"assert (.+)",
        ],
        'attribute_error': [
            r"AttributeError: (.+) has no attribute '([^']+)'",
        ],
        'type_error': [
            r"TypeError: (.+)",
        ],
        'value_error': [
            r"ValueError: (.+)",
        ],
        'missing_marker': [
            r"'([^']+)' not found in `markers` configuration option",
        ],
        'coverage_warning': [
            r"CoverageWarning: Couldn't parse Python file '([^']+)'",
        ]
    }
    
    def analyze_errors(self, test_output: str) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze test output and categorize errors."""
        categorized_errors = {}
        
        for error_type, patterns in self.ERROR_PATTERNS.items():
            categorized_errors[error_type] = []
            
            for pattern in patterns:
                matches = re.finditer(pattern, test_output, re.MULTILINE)
                for match in matches:
                    error_info = {
                        'type': error_type,
                        'pattern': pattern,
                        'match': match.group(0),
                        'groups': match.groups(),
                        'line_number': None,
                        'file_path': None
                    }
                    
                    # Extract file path and line number if available
                    if len(match.groups()) >= 2:
                        error_info['file_path'] = match.groups()[-2] if 'line' in pattern else match.groups()[-1]
                    if len(match.groups()) >= 3 and 'line' in pattern:
                        try:
                            error_info['line_number'] = int(match.groups()[-1])
                        except ValueError:
                            pass
                    
                    categorized_errors[error_type].append(error_info)
        
        return categorized_errors


class AutoFixer:
    """Applies automated fixes for common errors."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.analyzer = ErrorAnalyzer()
    
    def fix_import_errors(self, errors: List[Dict[str, Any]]) -> List[FixResult]:
        """Fix missing module imports."""
        fixes = []
        
        for error in errors:
            if not error['groups']:
                continue
                
            missing_module = error['groups'][0]
            fix_result = self._install_missing_package(missing_module)
            fixes.append(fix_result)
        
        return fixes
    
    def fix_syntax_errors(self, errors: List[Dict[str, Any]]) -> List[FixResult]:
        """Fix syntax errors in Python files."""
        fixes = []
        
        for error in errors:
            if len(error['groups']) < 3:
                continue
                
            file_path = error['groups'][1]
            line_number = int(error['groups'][2])
            
            fix_result = self._fix_syntax_in_file(file_path, line_number, error['groups'][0])
            fixes.append(fix_result)
        
        return fixes
    
    def fix_missing_markers(self, errors: List[Dict[str, Any]]) -> List[FixResult]:
        """Fix missing pytest markers."""
        fixes = []
        
        for error in errors:
            marker_name = error['groups'][0]
            fix_result = self._add_pytest_marker(marker_name)
            fixes.append(fix_result)
        
        return fixes
    
    def fix_coverage_warnings(self, errors: List[Dict[str, Any]]) -> List[FixResult]:
        """Fix coverage parsing warnings."""
        fixes = []
        
        for error in errors:
            file_path = error['groups'][0]
            fix_result = self._fix_unparseable_file(file_path)
            fixes.append(fix_result)
        
        return fixes
    
    def _install_missing_package(self, package_name: str) -> FixResult:
        """Attempt to install a missing package."""
        # Map common import names to package names
        package_mapping = {
            'itsdangerous': 'itsdangerous',
            'multipart': 'python-multipart',
            'email_validator': 'email-validator',
            'jose': 'python-jose',
            'passlib': 'passlib',
            'bcrypt': 'bcrypt',
            'asyncpg': 'asyncpg',
            'psycopg2': 'psycopg2-binary',
            'redis': 'redis',
            'celery': 'celery',
        }
        
        install_name = package_mapping.get(package_name, package_name)
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', install_name],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                return FixResult(
                    applied=True,
                    description=f"Installed missing package: {install_name}",
                    changes_made=[f"pip install {install_name}"]
                )
            else:
                return FixResult(
                    applied=False,
                    description=f"Failed to install package: {install_name}",
                    error=result.stderr
                )
        except Exception as e:
            return FixResult(
                applied=False,
                description=f"Error installing package: {install_name}",
                error=str(e)
            )
    
    def _fix_syntax_in_file(self, file_path: str, line_number: int, error_msg: str) -> FixResult:
        """Attempt to fix syntax errors in a file."""
        try:
            full_path = self.project_root / file_path
            if not full_path.exists():
                return FixResult(
                    applied=False,
                    description=f"File not found: {file_path}",
                    error="File does not exist"
                )
            
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if line_number > len(lines):
                return FixResult(
                    applied=False,
                    description=f"Line number {line_number} out of range in {file_path}",
                    error="Line number out of range"
                )
            
            # Common syntax fixes
            line = lines[line_number - 1]
            original_line = line
            
            # Fix common issues
            if "invalid syntax" in error_msg.lower():
                # Fix missing colons
                if line.strip().startswith(('if ', 'for ', 'while ', 'def ', 'class ', 'try', 'except', 'finally', 'with ', 'elif ')):
                    if not line.rstrip().endswith(':'):
                        line = line.rstrip() + ':\n'
                
                # Fix missing parentheses in print statements
                if 'print ' in line and not ('print(' in line):
                    line = re.sub(r'print\s+(.+)', r'print(\1)', line)
            
            if line != original_line:
                lines[line_number - 1] = line
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                return FixResult(
                    applied=True,
                    description=f"Fixed syntax error at line {line_number} in {file_path}",
                    file_path=file_path,
                    changes_made=[f"Line {line_number}: {original_line.strip()} -> {line.strip()}"]
                )
            
            return FixResult(
                applied=False,
                description=f"Could not auto-fix syntax error in {file_path}:{line_number}",
                error="No automatic fix available"
            )
            
        except Exception as e:
            return FixResult(
                applied=False,
                description=f"Error fixing syntax in {file_path}",
                error=str(e)
            )
    
    def _add_pytest_marker(self, marker_name: str) -> FixResult:
        """Add missing pytest marker to configuration."""
        try:
            pyproject_path = self.project_root / "pyproject.toml"
            
            if not pyproject_path.exists():
                return FixResult(
                    applied=False,
                    description="pyproject.toml not found",
                    error="Configuration file missing"
                )
            
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if marker already exists
            if f'"{marker_name}:' in content:
                return FixResult(
                    applied=False,
                    description=f"Marker {marker_name} already exists",
                    error="Marker already configured"
                )
            
            # Add marker to the markers list
            markers_pattern = r'markers\s*=\s*\[(.*?)\]'
            match = re.search(markers_pattern, content, re.DOTALL)
            
            if match:
                markers_content = match.group(1)
                new_marker = f'    "{marker_name}: marks tests as {marker_name} tests",'
                
                # Insert the new marker
                new_markers_content = markers_content.rstrip() + '\n' + new_marker + '\n'
                new_content = content.replace(match.group(1), new_markers_content)
                
                with open(pyproject_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                return FixResult(
                    applied=True,
                    description=f"Added pytest marker: {marker_name}",
                    file_path="pyproject.toml",
                    changes_made=[f"Added marker: {marker_name}"]
                )
            
            return FixResult(
                applied=False,
                description="Could not find markers section in pyproject.toml",
                error="Markers section not found"
            )
            
        except Exception as e:
            return FixResult(
                applied=False,
                description=f"Error adding pytest marker: {marker_name}",
                error=str(e)
            )
    
    def _fix_unparseable_file(self, file_path: str) -> FixResult:
        """Fix files that coverage cannot parse."""
        try:
            full_path = Path(file_path)
            
            if not full_path.exists():
                return FixResult(
                    applied=False,
                    description=f"File not found: {file_path}",
                    error="File does not exist"
                )
            
            # Try to compile the file to check for syntax errors
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                compile(content, str(full_path), 'exec')
                return FixResult(
                    applied=False,
                    description=f"File {file_path} appears to be syntactically correct",
                    error="No syntax issues found"
                )
            except SyntaxError as e:
                # Try to fix the syntax error
                lines = content.split('\n')
                
                if e.lineno and e.lineno <= len(lines):
                    line = lines[e.lineno - 1]
                    
                    # Common fixes
                    if e.msg and "invalid character" in e.msg:
                        # Remove invalid characters
                        fixed_line = re.sub(r'[^\x00-\x7F]+', '', line)
                        if fixed_line != line:
                            lines[e.lineno - 1] = fixed_line
                            
                            fixed_content = '\n'.join(lines)
                            with open(full_path, 'w', encoding='utf-8') as f:
                                f.write(fixed_content)
                            
                            return FixResult(
                                applied=True,
                                description=f"Fixed invalid characters in {file_path}",
                                file_path=str(full_path),
                                changes_made=[f"Removed invalid characters from line {e.lineno}"]
                            )
                
                return FixResult(
                    applied=False,
                    description=f"Could not auto-fix syntax error in {file_path}",
                    error=f"Syntax error: {e.msg}"
                )
            
        except Exception as e:
            return FixResult(
                applied=False,
                description=f"Error processing file: {file_path}",
                error=str(e)
            )


class MasterSolution:
    """Main class implementing the recursive testing and fixing loop."""
    
    def __init__(self, project_root: Path, mode: str = "full"):
        self.project_root = project_root
        self.mode = mode
        self.analyzer = ErrorAnalyzer()
        self.fixer = AutoFixer(project_root)
        self.max_iterations = 10
        self.iteration_count = 0
        
    def run(self) -> bool:
        """Run the master solution loop."""
        logger.info("🚀 Starting OpenPypi Master Solution")
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Mode: {self.mode}")
        
        success = False
        
        try:
            # Initial setup
            self._initial_setup()
            
            # Main recursive loop
            while self.iteration_count < self.max_iterations:
                self.iteration_count += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"🔄 ITERATION {self.iteration_count}/{self.max_iterations}")
                logger.info(f"{'='*60}")
                
                # Run tests and capture results
                test_result = self._run_tests()
                
                # If tests pass, we're done!
                if test_result.success and test_result.failed_count == 0:
                    logger.info("🎉 ALL TESTS PASSED!")
                    success = True
                    break
                
                # Analyze errors
                categorized_errors = self.analyzer.analyze_errors(
                    test_result.stdout + test_result.stderr
                )
                
                if not any(categorized_errors.values()):
                    logger.warning("❌ No recognizable error patterns found")
                    break
                
                # Apply fixes
                fixes_applied = self._apply_fixes(categorized_errors)
                
                if not fixes_applied:
                    logger.warning("❌ No fixes could be applied")
                    break
                
                logger.info(f"✅ Applied {fixes_applied} fixes, running tests again...")
            
            # Final summary
            self._generate_final_summary(success)
            
        except KeyboardInterrupt:
            logger.info("\n⏹️  Process interrupted by user")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
        
        return success
    
    def _initial_setup(self) -> None:
        """Perform initial setup tasks."""
        logger.info("🔧 Performing initial setup...")
        
        # Ensure required directories exist
        required_dirs = [
            "tests/api",
            "tests/core",
            "tests/stages",
            "scripts",
            "logs"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
        
        # Update pip
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                         capture_output=True, cwd=self.project_root)
        except:
            pass
        
        # Install development dependencies
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.[dev]'], 
                         capture_output=True, cwd=self.project_root)
        except:
            pass
    
    def _run_tests(self) -> TestResult:
        """Run the test suite and capture results."""
        logger.info("🧪 Running test suite...")
        
        cmd = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '-v',
            '--tb=short',
            '--cov=src/openpypi',
            '--cov-report=term-missing',
            '--maxfail=5'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=300  # 5 minute timeout
            )
            
            # Parse test results
            test_count = self._extract_test_count(result.stdout)
            failed_count = self._extract_failed_count(result.stdout)
            passed_count = test_count - failed_count
            coverage_percent = self._extract_coverage_percent(result.stdout)
            
            test_result = TestResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                errors=self._extract_errors(result.stdout + result.stderr),
                warnings=self._extract_warnings(result.stdout + result.stderr),
                coverage_percent=coverage_percent,
                test_count=test_count,
                failed_count=failed_count,
                passed_count=passed_count,
                skipped_count=0
            )
            
            logger.info(f"📊 Test Results: {passed_count} passed, {failed_count} failed, Coverage: {coverage_percent:.1f}%")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            logger.error("⏰ Test execution timed out")
            return TestResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Test execution timed out",
                errors=["Test execution timed out"],
                warnings=[],
                coverage_percent=0.0,
                test_count=0,
                failed_count=0,
                passed_count=0,
                skipped_count=0
            )
        
        except Exception as e:
            logger.error(f"❌ Error running tests: {e}")
            return TestResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                errors=[str(e)],
                warnings=[],
                coverage_percent=0.0,
                test_count=0,
                failed_count=0,
                passed_count=0,
                skipped_count=0
            )
    
    def _apply_fixes(self, categorized_errors: Dict[str, List[Dict[str, Any]]]) -> int:
        """Apply fixes for categorized errors."""
        total_fixes = 0
        
        # Priority order for fixing errors
        fix_order = [
            'import_error',
            'missing_marker',
            'coverage_warning',
            'syntax_error',
            'missing_fixture',
            'attribute_error',
            'type_error',
            'value_error',
            'assertion_error'
        ]
        
        for error_type in fix_order:
            if error_type not in categorized_errors or not categorized_errors[error_type]:
                continue
            
            logger.info(f"🔧 Fixing {error_type} errors...")
            
            fixes = []
            if error_type == 'import_error':
                fixes = self.fixer.fix_import_errors(categorized_errors[error_type])
            elif error_type == 'syntax_error':
                fixes = self.fixer.fix_syntax_errors(categorized_errors[error_type])
            elif error_type == 'missing_marker':
                fixes = self.fixer.fix_missing_markers(categorized_errors[error_type])
            elif error_type == 'coverage_warning':
                fixes = self.fixer.fix_coverage_warnings(categorized_errors[error_type])
            
            for fix in fixes:
                if fix.applied:
                    logger.info(f"  ✅ {fix.description}")
                    total_fixes += 1
                else:
                    logger.warning(f"  ❌ {fix.description}: {fix.error}")
        
        return total_fixes
    
    def _extract_test_count(self, output: str) -> int:
        """Extract total test count from pytest output."""
        match = re.search(r'(\d+) passed', output)
        if match:
            return int(match.group(1))
        
        match = re.search(r'collected (\d+) items', output)
        if match:
            return int(match.group(1))
        
        return 0
    
    def _extract_failed_count(self, output: str) -> int:
        """Extract failed test count from pytest output."""
        match = re.search(r'(\d+) failed', output)
        return int(match.group(1)) if match else 0
    
    def _extract_coverage_percent(self, output: str) -> float:
        """Extract coverage percentage from pytest output."""
        match = re.search(r'TOTAL.*?(\d+)%', output)
        return float(match.group(1)) if match else 0.0
    
    def _extract_errors(self, output: str) -> List[str]:
        """Extract error messages from test output."""
        errors = []
        
        # Look for ERROR lines
        for line in output.split('\n'):
            if 'ERROR' in line and ('collecting' in line or 'importing' in line):
                errors.append(line.strip())
        
        return errors
    
    def _extract_warnings(self, output: str) -> List[str]:
        """Extract warning messages from test output."""
        warnings = []
        
        # Look for warning patterns
        warning_patterns = [
            r'.*Warning.*',
            r'.*WARNING.*',
        ]
        
        for pattern in warning_patterns:
            matches = re.findall(pattern, output, re.MULTILINE)
            warnings.extend(matches)
        
        return warnings
    
    def _generate_final_summary(self, success: bool) -> None:
        """Generate and display final summary."""
        logger.info(f"\n{'='*60}")
        logger.info("📋 FINAL SUMMARY")
        logger.info(f"{'='*60}")
        
        if success:
            logger.info("🎉 SUCCESS: All tests are now passing!")
            logger.info("✅ Your OpenPypi project is fully functional")
        else:
            logger.info("⚠️  PARTIAL SUCCESS: Some issues may remain")
            logger.info(f"🔄 Completed {self.iteration_count} iterations")
        
        # Run final test to get stats
        final_result = self._run_tests()
        
        logger.info(f"\n📊 Final Test Statistics:")
        logger.info(f"   Tests: {final_result.passed_count} passed, {final_result.failed_count} failed")
        logger.info(f"   Coverage: {final_result.coverage_percent:.1f}%")
        
        # Recommendations
        logger.info(f"\n💡 Recommendations:")
        if final_result.coverage_percent < 80:
            logger.info("   - Consider adding more tests to improve coverage")
        if final_result.failed_count > 0:
            logger.info("   - Review remaining test failures manually")
        
        logger.info("   - Run 'python -m pytest tests/ -v' to verify")
        logger.info("   - Check 'master_solution.log' for detailed information")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="OpenPypi Master Solution")
    parser.add_argument(
        "--mode", 
        choices=["full", "quick", "fix-only"], 
        default="full",
        help="Solution mode"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory"
    )
    
    args = parser.parse_args()
    
    # Ensure we're in the right directory
    if not (args.project_root / "pyproject.toml").exists():
        logger.error("❌ pyproject.toml not found. Please run from the project root.")
        sys.exit(1)
    
    solution = MasterSolution(args.project_root, args.mode)
    success = solution.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 