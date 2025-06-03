class CodeValidator:
    """Validates Python code quality and correctness."""

    def __init__(self):
        self.python_keywords = {
            "False",
            "None",
            "True",
            "and",
            "as",
            "assert",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "try",
            "while",
            "with",
            "yield",
        }

    def validate_syntax(self, code: str) -> Tuple[bool, List[str]]:
        """
        Validate Python syntax.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            ast.parse(code)
            return True, []
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
        except Exception as e:
            errors.append(f"Parse error: {str(e)}")

        return False, errors

    def validate_imports(self, code: str) -> Tuple[bool, List[str]]:
        """
        Validate import statements.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("."):
                            issues.append(f"Relative import without 'from': {alias.name}")

                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.level == 0:
                        # Check for common problematic imports
                        if node.module in ["os", "sys"] and any(
                            alias.name in ["system", "exec", "eval"] for alias in node.names
                        ):
                            issues.append(f"Potentially unsafe import: {node.module}")

        except Exception as e:
            issues.append(f"Import validation error: {str(e)}")

        return len(issues) == 0, issues

    def validate_naming_conventions(self, code: str) -> Tuple[bool, List[str]]:
        """
        Validate Python naming conventions (PEP 8).

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not self._is_snake_case(node.name):
                        issues.append(f"Function '{node.name}' should use snake_case")

                elif isinstance(node, ast.ClassDef):
                    if not self._is_pascal_case(node.name):
                        issues.append(f"Class '{node.name}' should use PascalCase")

                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    if node.id.isupper() and len(node.id) > 1:
                        # Constants are OK
                        continue
                    elif not self._is_snake_case(node.id) and node.id not in self.python_keywords:
                        issues.append(f"Variable '{node.id}' should use snake_case")

        except Exception as e:
            issues.append(f"Naming validation error: {str(e)}")

        return len(issues) == 0, issues

    def _is_snake_case(self, name: str) -> bool:
        """Check if name follows snake_case convention."""
        return re.match(r"^[a-z_][a-z0-9_]*$", name) is not None

    def _is_pascal_case(self, name: str) -> bool:
        """Check if name follows PascalCase convention."""
        return re.match(r"^[A-Z][a-zA-Z0-9]*$", name) is not None

    def validate_docstrings(self, code: str) -> Tuple[bool, List[str]]:
        """
        Validate docstring presence and format.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                    if not ast.get_docstring(node):
                        issues.append(f"{type(node).__name__} '{node.name}' missing docstring")
                    else:
                        docstring = ast.get_docstring(node)
                        if len(docstring.strip()) < 10:
                            issues.append(
                                f"{type(node).__name__} '{node.name}' has very short docstring"
                            )

        except Exception as e:
            issues.append(f"Docstring validation error: {str(e)}")

        return len(issues) == 0, issues

    def validate_type_hints(self, code: str) -> Tuple[bool, List[str]]:
        """
        Validate type hint usage.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip special methods
                    if node.name.startswith("__") and node.name.endswith("__"):
                        continue

                    # Check return type annotation
                    if not node.returns:
                        issues.append(f"Function '{node.name}' missing return type annotation")

                    # Check argument type annotations
                    for arg in node.args.args:
                        if not arg.annotation and arg.arg != "self" and arg.arg != "cls":
                            issues.append(
                                f"Argument '{arg.arg}' in function '{node.name}' missing type annotation"
                            )

        except Exception as e:
            issues.append(f"Type hint validation error: {str(e)}")

        return len(issues) == 0, issues

    def validate_complexity(self, code: str, max_complexity: int = 10) -> Tuple[bool, List[str]]:
        """
        Validate cyclomatic complexity.

        Args:
            code: Python code to validate
            max_complexity: Maximum allowed complexity

        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = self._calculate_complexity(node)
                    if complexity > max_complexity:
                        issues.append(
                            f"Function '{node.name}' has complexity {complexity} "
                            f"(max: {max_complexity})"
                        )

        except Exception as e:
            issues.append(f"Complexity validation error: {str(e)}")

        return len(issues) == 0, issues

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity


class PackageValidator:
    """Validates package structure and metadata."""

    def __init__(self):
        self.required_files = {
            "pyproject.toml": "Package configuration file",
            "README.md": "Package documentation",
            "LICENSE": "License file",
        }

        self.recommended_files = {
            "CHANGELOG.md": "Change log",
            ".gitignore": "Git ignore file",
            "requirements.txt": "Dependencies file",
        }

    def validate_structure(self, package_dir: Path) -> Dict[str, Any]:
        """
        Validate package directory structure.

        Args:
            package_dir: Path to package directory

        Returns:
            Dict containing validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_files": [],
            "found_files": [],
            "structure_score": 0.0,
        }

        if not package_dir.exists():
            results["valid"] = False
            results["errors"].append(f"Package directory does not exist: {package_dir}")
            return results

        # Check required files
        for filename, description in self.required_files.items():
            file_path = package_dir / filename
            if file_path.exists():
                results["found_files"].append(filename)
            else:
                results["missing_files"].append(filename)
                results["errors"].append(f"Missing required file: {filename} ({description})")
                results["valid"] = False

        # Check recommended files
        for filename, description in self.recommended_files.items():
            file_path = package_dir / filename
            if not file_path.exists():
                results["warnings"].append(f"Missing recommended file: {filename} ({description})")

        # Check for source directory
        src_dirs = ["src", package_dir.name]
        src_found = False
        for src_dir in src_dirs:
            if (package_dir / src_dir).exists():
                src_found = True
                break

        if not src_found:
            results["errors"].append("No source directory found (expected 'src' or package name)")
            results["valid"] = False

        # Check for tests directory
        test_dirs = ["tests", "test"]
        test_found = any((package_dir / test_dir).exists() for test_dir in test_dirs)

        if not test_found:
            results["warnings"].append("No tests directory found")

        # Calculate structure score
        total_files = len(self.required_files) + len(self.recommended_files)
        found_files = len(results["found_files"]) + len(
            [f for f in self.recommended_files if (package_dir / f).exists()]
        )

        results["structure_score"] = (found_files / total_files) * 100

        return results

    def validate_pyproject_toml(self, pyproject_path: Path) -> Dict[str, Any]:
        """
        Validate pyproject.toml file.

        Args:
            pyproject_path: Path to pyproject.toml

        Returns:
            Dict containing validation results
        """
        results = {"valid": True, "errors": [], "warnings": [], "metadata": {}}

        if not pyproject_path.exists():
            results["valid"] = False
            results["errors"].append("pyproject.toml file not found")
            return results

        try:
            import toml

            data = toml.load(pyproject_path)

            # Check build system
            if "build-system" not in data:
                results["errors"].append("Missing [build-system] section")
                results["valid"] = False

            # Check project metadata
            if "project" not in data:
                results["errors"].append("Missing [project] section")
                results["valid"] = False
            else:
                project = data["project"]
                results["metadata"] = project

                # Required fields
                required_fields = ["name", "version", "description"]
                for field in required_fields:
                    if field not in project:
                        results["errors"].append(f"Missing required field: project.{field}")
                        results["valid"] = False

                # Recommended fields
                recommended_fields = ["authors", "license", "readme", "requires-python"]
                for field in recommended_fields:
                    if field not in project:
                        results["warnings"].append(f"Missing recommended field: project.{field}")

                # Validate version format
                if "version" in project:
                    version = project["version"]
                    if not re.match(r"^\d+\.\d+\.\d+", version):
                        results["warnings"].append(
                            f"Version '{version}' doesn't follow semantic versioning"
                        )

        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Failed to parse pyproject.toml: {str(e)}")

        return results

    def validate_dependencies(self, package_dir: Path) -> Dict[str, Any]:
        """
        Validate package dependencies.

        Args:
            package_dir: Path to package directory

        Returns:
            Dict containing validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "dependencies": [],
            "security_issues": [],
        }

        # Check pyproject.toml dependencies
        pyproject_path = package_dir / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import toml

                data = toml.load(pyproject_path)

                project = data.get("project", {})
                dependencies = project.get("dependencies", [])
                results["dependencies"] = dependencies

                # Check for common security issues
                for dep in dependencies:
                    if any(unsafe in dep.lower() for unsafe in ["eval", "exec", "pickle"]):
                        results["security_issues"].append(f"Potentially unsafe dependency: {dep}")

            except Exception as e:
                results["errors"].append(f"Failed to parse dependencies: {str(e)}")
                results["valid"] = False

        # Check requirements.txt
        requirements_path = package_dir / "requirements.txt"
        if requirements_path.exists():
            try:
                requirements = requirements_path.read_text().strip().split("\n")
                requirements = [
                    req.strip() for req in requirements if req.strip() and not req.startswith("#")
                ]

                # Merge with pyproject.toml dependencies
                all_deps = set(results["dependencies"] + requirements)
                results["dependencies"] = list(all_deps)

            except Exception as e:
                results["warnings"].append(f"Failed to parse requirements.txt: {str(e)}")

        return results


class SecurityValidator:
    """Validates security aspects of Python code."""

    def __init__(self):
        self.dangerous_functions = {
            "eval",
            "exec",
            "compile",
            "__import__",
            "open",
            "input",
            "raw_input",
        }
        self.dangerous_modules = {
            "os.system",
            "subprocess.call",
            "subprocess.run",
            "pickle.loads",
            "pickle.load",
            "marshal.loads",
        }

        self.security_patterns = [
            (r"shell\s*=\s*True", "Shell injection risk"),
            (r"eval\s*\(", "Code injection risk"),
            (r"exec\s*\(", "Code execution risk"),
            (r"__import__\s*\(", "Dynamic import risk"),
            (r"pickle\.loads?\s*\(", "Pickle deserialization risk"),
            (r"yaml\.load\s*\((?!.*Loader)", "Unsafe YAML loading"),
            (r"requests\.get\s*\([^)]*verify\s*=\s*False", "SSL verification disabled"),
        ]

    def validate_security(self, code: str) -> Dict[str, Any]:
        """
        Validate security aspects of Python code.

        Args:
            code: Python code to validate

        Returns:
            Dict containing security validation results
        """
        results = {
            "secure": True,
            "high_risk": [],
            "medium_risk": [],
            "low_risk": [],
            "recommendations": [],
        }

        # Check for dangerous function calls
        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = self._get_function_name(node.func)

                    if func_name in self.dangerous_functions:
                        results["high_risk"].append(
                            f"Dangerous function call: {func_name} at line {node.lineno}"
                        )
                        results["secure"] = False

                    # Check subprocess calls with shell=True
                    if func_name in ["subprocess.call", "subprocess.run", "subprocess.Popen"]:
                        for keyword in node.keywords:
                            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant):
                                if keyword.value.value is True:
                                    results["high_risk"].append(
                                        f"Shell injection risk: {func_name} with shell=True at line {node.lineno}"
                                    )
                                    results["secure"] = False

        except Exception as e:
            results["medium_risk"].append(f"Security analysis error: {str(e)}")

        # Check for security patterns using regex
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            for pattern, description in self.security_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    results["medium_risk"].append(f"{description} at line {i}: {line.strip()}")
                    if results["secure"]:
                        results["secure"] = len(results["high_risk"]) == 0

        # Generate recommendations
        if results["high_risk"]:
            results["recommendations"].append("Review and replace dangerous function calls")
        if results["medium_risk"]:
            results["recommendations"].append("Consider security implications of flagged patterns")
        if not results["high_risk"] and not results["medium_risk"]:
            results["recommendations"].append(
                "Code appears secure, but consider additional security review"
            )

        return results

    def _get_function_name(self, node: ast.AST) -> str:
        """Extract function name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_function_name(node.value)
            return f"{value_name}.{node.attr}"
        else:
            return "unknown"

    def scan_dependencies_security(self, dependencies: List[str]) -> Dict[str, Any]:
        """
        Scan dependencies for known security vulnerabilities.

        Args:
            dependencies: List of dependency strings

        Returns:
            Dict containing security scan results
        """
        results = {"secure": True, "vulnerabilities": [], "warnings": [], "scanned_packages": []}

        try:
            # Try to use safety to check for known vulnerabilities
            import subprocess
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                for dep in dependencies:
                    f.write(f"{dep}\n")
                f.flush()

                try:
                    result = subprocess.run(
                        ["safety", "check", "-r", f.name, "--json"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    if result.returncode == 0:
                        # No vulnerabilities found
                        results["scanned_packages"] = dependencies
                    else:
                        # Parse safety output
                        try:
                            import json

                            safety_data = json.loads(result.stdout)
                            for vuln in safety_data:
                                results["vulnerabilities"].append(
                                    {
                                        "package": vuln.get("package_name"),
                                        "version": vuln.get("analyzed_version"),
                                        "vulnerability": vuln.get("vulnerability_id"),
                                        "severity": vuln.get("severity", "unknown"),
                                    }
                                )
                            results["secure"] = False
                        except json.JSONDecodeError:
                            results["warnings"].append("Failed to parse safety output")

                except subprocess.TimeoutExpired:
                    results["warnings"].append("Security scan timed out")
                except FileNotFoundError:
                    results["warnings"].append(
                        "Safety tool not installed - skipping vulnerability scan"
                    )

        except Exception as e:
            results["warnings"].append(f"Security scan error: {str(e)}")

        return results


class TestValidator:
    """Validates test quality and coverage."""

    def __init__(self):
        self.test_frameworks = ["pytest", "unittest", "nose2"]
        self.test_patterns = [r"def test_", r"class Test", r"@pytest\.", r"unittest\.TestCase"]

    def validate_tests(self, package_dir: Path) -> Dict[str, Any]:
        """
        Validate test structure and quality.

        Args:
            package_dir: Path to package directory

        Returns:
            Dict containing test validation results
        """
        results = {
            "has_tests": False,
            "test_files": [],
            "test_functions": 0,
            "test_classes": 0,
            "coverage_configurable": False,
            "framework_detected": None,
            "recommendations": [],
        }

        # Find test directories
        test_dirs = []
        for test_dir_name in ["tests", "test"]:
            test_dir = package_dir / test_dir_name
            if test_dir.exists():
                test_dirs.append(test_dir)

        if not test_dirs:
            results["recommendations"].append("Create a tests directory")
            return results

        results["has_tests"] = True

        # Analyze test files
        for test_dir in test_dirs:
            for test_file in test_dir.rglob("*.py"):
                if test_file.name.startswith("test_") or test_file.name.endswith("_test.py"):
                    results["test_files"].append(str(test_file.relative_to(package_dir)))

                    # Analyze test file content
                    try:
                        content = test_file.read_text()
                        test_analysis = self._analyze_test_file(content)
                        results["test_functions"] += test_analysis["functions"]
                        results["test_classes"] += test_analysis["classes"]

                        if not results["framework_detected"] and test_analysis["framework"]:
                            results["framework_detected"] = test_analysis["framework"]

                    except Exception as e:
                        results["recommendations"].append(
                            f"Failed to analyze {test_file}: {str(e)}"
                        )

        # Check for coverage configuration
        coverage_files = [".coveragerc", "pyproject.toml", "setup.cfg"]
        for coverage_file in coverage_files:
            if (package_dir / coverage_file).exists():
                results["coverage_configurable"] = True
                break

        # Generate recommendations
        if results["test_functions"] == 0:
            results["recommendations"].append("Add test functions")
        elif results["test_functions"] < 5:
            results["recommendations"].append("Consider adding more comprehensive tests")

        if not results["coverage_configurable"]:
            results["recommendations"].append("Configure test coverage measurement")

        if not results["framework_detected"]:
            results["recommendations"].append(
                "Use a recognized test framework (pytest recommended)"
            )

        return results

    def _analyze_test_file(self, content: str) -> Dict[str, Any]:
        """Analyze individual test file."""
        analysis = {"functions": 0, "classes": 0, "framework": None}

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith("test_"):
                        analysis["functions"] += 1

                elif isinstance(node, ast.ClassDef):
                    if node.name.startswith("Test"):
                        analysis["classes"] += 1

            # Detect framework
            if "pytest" in content:
                analysis["framework"] = "pytest"
            elif "unittest" in content:
                analysis["framework"] = "unittest"
            elif "nose" in content:
                analysis["framework"] = "nose2"

        except Exception:
            pass

        return analysis

    def run_coverage_analysis(self, package_dir: Path) -> Dict[str, Any]:
        """
        Run coverage analysis on tests.

        Args:
            package_dir: Path to package directory

        Returns:
            Dict containing coverage results
        """
        results = {
            "coverage_available": False,
            "total_coverage": 0.0,
            "file_coverage": {},
            "missing_lines": {},
            "recommendations": [],
        }

        try:
            import json
            import subprocess

            # Try to run coverage
            cmd = [
                sys.executable,
                "-m",
                "coverage",
                "run",
                "-m",
                "pytest",
                "--cov-report=json",
                "--cov-report=term",
            ]

            result = subprocess.run(
                cmd, cwd=package_dir, capture_output=True, text=True, timeout=60
            )

            # Look for coverage.json
            coverage_file = package_dir / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)

                results["coverage_available"] = True
                results["total_coverage"] = coverage_data.get("totals", {}).get(
                    "percent_covered", 0
                )

                # File-level coverage
                files = coverage_data.get("files", {})
                for filename, file_data in files.items():
                    results["file_coverage"][filename] = file_data.get("summary", {}).get(
                        "percent_covered", 0
                    )

                    missing = file_data.get("missing_lines", [])
                    if missing:
                        results["missing_lines"][filename] = missing

                # Generate recommendations
                if results["total_coverage"] < 80:
                    results["recommendations"].append("Increase test coverage to at least 80%")
                elif results["total_coverage"] < 90:
                    results["recommendations"].append("Consider increasing coverage to 90%+")

                low_coverage_files = [f for f, cov in results["file_coverage"].items() if cov < 70]
                if low_coverage_files:
                    results["recommendations"].append(
                        f"Focus on testing these low-coverage files: {', '.join(low_coverage_files[:3])}"
                    )

        except subprocess.TimeoutExpired:
            results["recommendations"].append("Coverage analysis timed out")
        except FileNotFoundError:
            results["recommendations"].append("Coverage tool not available")
        except Exception as e:
            results["recommendations"].append(f"Coverage analysis failed: {str(e)}")

        return results


class DocumentationValidator:
    """Validates documentation quality and completeness."""

    def __init__(self):
        self.readme_sections = [
            "installation",
            "usage",
            "examples",
            "api",
            "contributing",
            "license",
        ]

        self.doc_formats = ["sphinx", "mkdocs", "gitbook"]

    def validate_readme(self, readme_path: Path) -> Dict[str, Any]:
        """
        Validate README file quality.

        Args:
            readme_path: Path to README file

        Returns:
            Dict containing README validation results
        """
        results = {
            "exists": False,
            "length": 0,
            "sections_found": [],
            "sections_missing": [],
            "has_badges": False,
            "has_examples": False,
            "quality_score": 0.0,
            "recommendations": [],
        }

        if not readme_path.exists():
            results["recommendations"].append("Create a README.md file")
            return results

        results["exists"] = True

        try:
            content = readme_path.read_text().lower()
            results["length"] = len(content)

            # Check for sections
            for section in self.readme_sections:
                if section in content:
                    results["sections_found"].append(section)
                else:
                    results["sections_missing"].append(section)

            # Check for badges
            if any(badge in content for badge in ["![", "https://img.shields.io", "badge"]):
                results["has_badges"] = True

            # Check for examples
            if any(example in content for example in ["```", "example", "usage"]):
                results["has_examples"] = True

            # Calculate quality score
            section_score = len(results["sections_found"]) / len(self.readme_sections)
            length_score = min(results["length"] / 1000, 1.0)  # 1000 chars = full score
            badge_score = 0.1 if results["has_badges"] else 0
            example_score = 0.2 if results["has_examples"] else 0

            results["quality_score"] = (
                section_score * 0.6 + length_score * 0.1 + badge_score + example_score
            ) * 100

            # Generate recommendations
            if results["length"] < 500:
                results["recommendations"].append(
                    "README is quite short - consider adding more detail"
                )

            if not results["has_examples"]:
                results["recommendations"].append("Add usage examples to README")

            if not results["has_badges"]:
                results["recommendations"].append("Consider adding status badges")

            for missing in results["sections_missing"][:3]:
                results["recommendations"].append(f"Add {missing} section to README")

        except Exception as e:
            results["recommendations"].append(f"Failed to analyze README: {str(e)}")

        return results

    def validate_docstrings(self, package_dir: Path) -> Dict[str, Any]:
        """
        Validate docstring coverage and quality.

        Args:
            package_dir: Path to package directory

        Returns:
            Dict containing docstring validation results
        """
        results = {
            "total_functions": 0,
            "documented_functions": 0,
            "total_classes": 0,
            "documented_classes": 0,
            "total_modules": 0,
            "documented_modules": 0,
            "coverage_percentage": 0.0,
            "quality_issues": [],
            "recommendations": [],
        }

        # Find Python source files
        src_dirs = ["src", package_dir.name]
        python_files = []

        for src_dir_name in src_dirs:
            src_dir = package_dir / src_dir_name
            if src_dir.exists():
                python_files.extend(src_dir.rglob("*.py"))
                break

        if not python_files:
            results["recommendations"].append("No Python source files found")
            return results

        for py_file in python_files:
            if py_file.name.startswith("__") and py_file.name.endswith("__.py"):
                continue  # Skip __init__.py, __main__.py etc.

            try:
                content = py_file.read_text()
                file_analysis = self._analyze_docstrings(content, py_file.name)

                results["total_functions"] += file_analysis["total_functions"]
                results["documented_functions"] += file_analysis["documented_functions"]
                results["total_classes"] += file_analysis["total_classes"]
                results["documented_classes"] += file_analysis["documented_classes"]
                results["total_modules"] += 1

                if file_analysis["has_module_docstring"]:
                    results["documented_modules"] += 1

                results["quality_issues"].extend(file_analysis["quality_issues"])

            except Exception as e:
                results["quality_issues"].append(f"Failed to analyze {py_file}: {str(e)}")

        # Calculate coverage
        total_items = (
            results["total_functions"] + results["total_classes"] + results["total_modules"]
        )
        documented_items = (
            results["documented_functions"]
            + results["documented_classes"]
            + results["documented_modules"]
        )

        if total_items > 0:
            results["coverage_percentage"] = (documented_items / total_items) * 100

        # Generate recommendations
        if results["coverage_percentage"] < 80:
            results["recommendations"].append("Increase docstring coverage to at least 80%")

        if results["total_modules"] > results["documented_modules"]:
            results["recommendations"].append("Add module-level docstrings")

        if results["quality_issues"]:
            results["recommendations"].append("Address docstring quality issues")

        return results

    def _analyze_docstrings(self, content: str, filename: str) -> Dict[str, Any]:
        """Analyze docstrings in a single file."""
        analysis = {
            "total_functions": 0,
            "documented_functions": 0,
            "total_classes": 0,
            "documented_classes": 0,
            "has_module_docstring": False,
            "quality_issues": [],
        }

        try:
            tree = ast.parse(content)

            # Check module docstring
            if ast.get_docstring(tree):
                analysis["has_module_docstring"] = True

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip private methods and special methods for now
                    if not node.name.startswith("_"):
                        analysis["total_functions"] += 1

                        docstring = ast.get_docstring(node)
                        if docstring:
                            analysis["documented_functions"] += 1

                            # Check docstring quality
                            if len(docstring.strip()) < 20:
                                analysis["quality_issues"].append(
                                    f"{filename}: Function '{node.name}' has very short docstring"
                                )
                        else:
                            analysis["quality_issues"].append(
                                f"{filename}: Function '{node.name}' missing docstring"
                            )

                elif isinstance(node, ast.ClassDef):
                    analysis["total_classes"] += 1

                    docstring = ast.get_docstring(node)
                    if docstring:
                        analysis["documented_classes"] += 1

                        if len(docstring.strip()) < 30:
                            analysis["quality_issues"].append(
                                f"{filename}: Class '{node.name}' has very short docstring"
                            )
                    else:
                        analysis["quality_issues"].append(
                            f"{filename}: Class '{node.name}' missing docstring"
                        )

        except Exception as e:
            analysis["quality_issues"].append(f"{filename}: Docstring analysis failed: {str(e)}")

        return analysis

    def validate_api_docs(self, package_dir: Path) -> Dict[str, Any]:
        """
        Validate API documentation structure.

        Args:
            package_dir: Path to package directory

        Returns:
            Dict containing API documentation validation results
        """
        results = {
            "has_docs_dir": False,
            "doc_format": None,
            "config_found": False,
            "api_docs_generated": False,
            "build_successful": False,
            "recommendations": [],
        }

        # Check for documentation directory
        docs_dir = package_dir / "docs"
        if docs_dir.exists():
            results["has_docs_dir"] = True

            # Detect documentation format
            if (docs_dir / "conf.py").exists() or (docs_dir / "source" / "conf.py").exists():
                results["doc_format"] = "sphinx"
                results["config_found"] = True
            elif (docs_dir / "mkdocs.yml").exists():
                results["doc_format"] = "mkdocs"
                results["config_found"] = True

            # Check for API documentation
            api_patterns = ["api.rst", "api.md", "reference.rst", "reference.md"]
            for pattern in api_patterns:
                if list(docs_dir.rglob(pattern)):
                    results["api_docs_generated"] = True
                    break

            # Try to build documentation
            if results["doc_format"] == "sphinx":
                results["build_successful"] = self._test_sphinx_build(docs_dir)
            elif results["doc_format"] == "mkdocs":
                results["build_successful"] = self._test_mkdocs_build(docs_dir)

        # Generate recommendations
        if not results["has_docs_dir"]:
            results["recommendations"].append("Create a docs directory with Sphinx or MkDocs")
        elif not results["config_found"]:
            results["recommendations"].append("Configure documentation build system")
        elif not results["api_docs_generated"]:
            results["recommendations"].append("Generate API reference documentation")
        elif not results["build_successful"]:
            results["recommendations"].append("Fix documentation build errors")

        return results

    def _test_sphinx_build(self, docs_dir: Path) -> bool:
        """Test if Sphinx documentation builds successfully."""
        try:
            import subprocess

            # Look for Makefile or make.bat
            if (docs_dir / "Makefile").exists():
                result = subprocess.run(
                    ["make", "html"], cwd=docs_dir, capture_output=True, timeout=60
                )
                return result.returncode == 0
            else:
                # Try direct sphinx-build
                source_dir = docs_dir / "source" if (docs_dir / "source").exists() else docs_dir
                build_dir = docs_dir / "build" / "html"

                result = subprocess.run(
                    ["sphinx-build", "-b", "html", str(source_dir), str(build_dir)],
                    capture_output=True,
                    timeout=60,
                )
                return result.returncode == 0

        except Exception:
            return False

    def _test_mkdocs_build(self, docs_dir: Path) -> bool:
        """Test if MkDocs documentation builds successfully."""
        try:
            import subprocess

            result = subprocess.run(
                ["mkdocs", "build"],
                cwd=docs_dir.parent,  # mkdocs.yml is usually in project root
                capture_output=True,
                timeout=60,
            )
            return result.returncode == 0

        except Exception:
            return False


class QualityValidator:
    """Comprehensive quality validator that combines all validation aspects."""

    def __init__(self):
        self.code_validator = CodeValidator()
        self.package_validator = PackageValidator()
        self.security_validator = SecurityValidator()
        self.test_validator = TestValidator()
        self.doc_validator = DocumentationValidator()

    async def validate_package_quality(
        self,
        package_dir: Path,
        run_tests: bool = True,
        check_security: bool = True,
        analyze_docs: bool = True,
    ) -> Dict[str, Any]:
        """
        Perform comprehensive package quality validation.

        Args:
            package_dir: Path to package directory
            run_tests: Whether to run test validation
            check_security: Whether to perform security checks
            analyze_docs: Whether to analyze documentation

        Returns:
            Dict containing comprehensive validation results
        """
        results = {
            "overall_score": 0.0,
            "grade": "F",
            "package_structure": {},
            "code_quality": {},
            "security": {},
            "tests": {},
            "documentation": {},
            "recommendations": [],
            "summary": {},
        }

        logger.info(f"Starting comprehensive quality validation for {package_dir}")

        # 1. Package Structure Validation
        logger.info("Validating package structure...")
        results["package_structure"] = self.package_validator.validate_structure(package_dir)

        # 2. Code Quality Validation
        logger.info("Validating code quality...")
        results["code_quality"] = await self._validate_all_code(package_dir)

        # 3. Security Validation
        if check_security:
            logger.info("Performing security validation...")
            results["security"] = await self._validate_security(package_dir)

        # 4. Test Validation
        if run_tests:
            logger.info("Validating tests...")
            results["tests"] = self.test_validator.validate_tests(package_dir)

            # Run coverage analysis if tests exist
            if results["tests"]["has_tests"]:
                coverage_results = self.test_validator.run_coverage_analysis(package_dir)
                results["tests"].update(coverage_results)

        # 5. Documentation Validation
        if analyze_docs:
            logger.info("Validating documentation...")
            results["documentation"] = await self._validate_documentation(package_dir)

        # 6. Calculate Overall Score and Grade
        results["overall_score"], results["grade"] = self._calculate_overall_score(results)

        # 7. Generate Summary and Recommendations
        results["summary"] = self._generate_summary(results)
        results["recommendations"] = self._generate_comprehensive_recommendations(results)

        logger.info(
            f"Quality validation completed. Overall score: {results['overall_score']:.1f} ({results['grade']})"
        )

        return results

    async def _validate_all_code(self, package_dir: Path) -> Dict[str, Any]:
        """Validate all Python code in the package."""
        results = {
            "files_analyzed": 0,
            "syntax_errors": [],
            "naming_issues": [],
            "docstring_issues": [],
            "type_hint_issues": [],
            "complexity_issues": [],
            "overall_quality_score": 0.0,
        }

        # Find all Python files
        python_files = []
        for pattern in ["*.py", "**/*.py"]:
            python_files.extend(package_dir.rglob(pattern))

        # Filter out __pycache__ and other non-source files
        python_files = [
            f for f in python_files if "__pycache__" not in str(f) and not f.name.startswith(".")
        ]

        results["files_analyzed"] = len(python_files)

        total_score = 0.0
        for py_file in python_files:
            try:
                content = py_file.read_text()
                file_score = 0.0

                # Syntax validation
                syntax_valid, syntax_errors = self.code_validator.validate_syntax(content)
                if not syntax_valid:
                    results["syntax_errors"].extend([f"{py_file}: {err}" for err in syntax_errors])
                else:
                    file_score += 25  # 25 points for valid syntax

                # Naming conventions
                naming_valid, naming_issues = self.code_validator.validate_naming_conventions(
                    content
                )
                if not naming_valid:
                    results["naming_issues"].extend(
                        [f"{py_file}: {issue}" for issue in naming_issues]
                    )
                else:
                    file_score += 20  # 20 points for good naming

                # Docstrings
                doc_valid, doc_issues = self.code_validator.validate_docstrings(content)
                if not doc_valid:
                    results["docstring_issues"].extend(
                        [f"{py_file}: {issue}" for issue in doc_issues]
                    )
                else:
                    file_score += 25  # 25 points for docstrings

                # Type hints
                type_valid, type_issues = self.code_validator.validate_type_hints(content)
                if not type_valid:
                    results["type_hint_issues"].extend(
                        [f"{py_file}: {issue}" for issue in type_issues]
                    )
                else:
                    file_score += 20  # 20 points for type hints

                # Complexity
                complexity_valid, complexity_issues = self.code_validator.validate_complexity(
                    content
                )
                if not complexity_valid:
                    results["complexity_issues"].extend(
                        [f"{py_file}: {issue}" for issue in complexity_issues]
                    )
                else:
                    file_score += 10  # 10 points for low complexity

                total_score += file_score

            except Exception as e:
                results["syntax_errors"].append(f"{py_file}: Failed to analyze - {str(e)}")

        # Calculate overall quality score
        if results["files_analyzed"] > 0:
            results["overall_quality_score"] = total_score / (results["files_analyzed"] * 100)

        return results

    async def _validate_security(self, package_dir: Path) -> Dict[str, Any]:
        """Validate security aspects of the package."""
        results = {
            "code_security": {"secure": True, "issues": []},
            "dependency_security": {"secure": True, "vulnerabilities": []},
            "overall_secure": True,
        }

        # Validate code security
        python_files = list(package_dir.rglob("*.py"))
        for py_file in python_files:
            try:
                content = py_file.read_text()
                security_results = self.security_validator.validate_security(content)

                if not security_results["secure"]:
                    results["code_security"]["secure"] = False
                    results["overall_secure"] = False

                # Collect all security issues
                all_issues = (
                    security_results["high_risk"]
                    + security_results["medium_risk"]
                    + security_results["low_risk"]
                )

                for issue in all_issues:
                    results["code_security"]["issues"].append(f"{py_file.name}: {issue}")

            except Exception as e:
                results["code_security"]["issues"].append(
                    f"{py_file}: Security analysis failed - {str(e)}"
                )

        # Validate dependency security
        pyproject_path = package_dir / "pyproject.toml"
        if pyproject_path.exists():
            dep_results = self.package_validator.validate_dependencies(package_dir)
            if dep_results["dependencies"]:
                security_scan = self.security_validator.scan_dependencies_security(
                    dep_results["dependencies"]
                )

                results["dependency_security"] = security_scan
                if not security_scan["secure"]:
                    results["overall_secure"] = False

        return results

    async def _validate_documentation(self, package_dir: Path) -> Dict[str, Any]:
        """Validate documentation quality."""
        results = {"readme": {}, "docstrings": {}, "api_docs": {}, "overall_doc_score": 0.0}

        # Validate README
        readme_files = ["README.md", "README.rst", "README.txt"]
        for readme_name in readme_files:
            readme_path = package_dir / readme_name
            if readme_path.exists():
                results["readme"] = self.doc_validator.validate_readme(readme_path)
                break

        if not results["readme"]:
            results["readme"] = {"exists": False, "quality_score": 0.0}

        # Validate docstrings
        results["docstrings"] = self.doc_validator.validate_docstrings(package_dir)

        # Validate API documentation
        results["api_docs"] = self.doc_validator.validate_api_docs(package_dir)

        # Calculate overall documentation score
        readme_score = results["readme"].get("quality_score", 0) * 0.4
        docstring_score = results["docstrings"].get("coverage_percentage", 0) * 0.4
        api_score = (100 if results["api_docs"].get("build_successful") else 0) * 0.2

        results["overall_doc_score"] = readme_score + docstring_score + api_score

        return results

    def _calculate_overall_score(self, results: Dict[str, Any]) -> Tuple[float, str]:
        """Calculate overall quality score and grade."""
        scores = []
        weights = []

        # Package structure (15%)
        if results["package_structure"]:
            structure_score = results["package_structure"].get("structure_score", 0)
            scores.append(structure_score)
            weights.append(0.15)

        # Code quality (30%)
        if results["code_quality"]:
            code_score = results["code_quality"].get("overall_quality_score", 0) * 100
            scores.append(code_score)
            weights.append(0.30)

        # Security (20%)
        if results["security"]:
            security_score = 100 if results["security"].get("overall_secure", False) else 50
            scores.append(security_score)
            weights.append(0.20)

        # Tests (20%)
        if results["tests"]:
            test_score = 0
            if results["tests"].get("has_tests", False):
                test_score += 50  # Base score for having tests
                coverage = results["tests"].get("total_coverage", 0)
                test_score += min(coverage * 0.5, 50)  # Up to 50 more for coverage
            scores.append(test_score)
            weights.append(0.20)

        # Documentation (15%)
        if results["documentation"]:
            doc_score = results["documentation"].get("overall_doc_score", 0)
            scores.append(doc_score)
            weights.append(0.15)

        # Calculate weighted average
        if scores and weights:
            overall_score = sum(score * weight for score, weight in zip(scores, weights)) / sum(
                weights
            )
        else:
            overall_score = 0.0

        # Determine grade
        if overall_score >= 90:
            grade = "A+"
        elif overall_score >= 85:
            grade = "A"
        elif overall_score >= 80:
            grade = "A-"
        elif overall_score >= 75:
            grade = "B+"
        elif overall_score >= 70:
            grade = "B"
        elif overall_score >= 65:
            grade = "B-"
        elif overall_score >= 60:
            grade = "C+"
        elif overall_score >= 55:
            grade = "C"
        elif overall_score >= 50:
            grade = "C-"
        elif overall_score >= 40:
            grade = "D"
        else:
            grade = "F"

        return overall_score, grade

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of validation results."""
        summary = {
            "total_files": 0,
            "total_issues": 0,
            "critical_issues": 0,
            "strengths": [],
            "weaknesses": [],
            "priority_fixes": [],
        }

        # Count files and issues
        if results["code_quality"]:
            summary["total_files"] = results["code_quality"].get("files_analyzed", 0)

            # Count issues
            syntax_errors = len(results["code_quality"].get("syntax_errors", []))
            naming_issues = len(results["code_quality"].get("naming_issues", []))
            doc_issues = len(results["code_quality"].get("docstring_issues", []))
            type_issues = len(results["code_quality"].get("type_hint_issues", []))
            complexity_issues = len(results["code_quality"].get("complexity_issues", []))

            summary["total_issues"] = (
                syntax_errors + naming_issues + doc_issues + type_issues + complexity_issues
            )
            summary["critical_issues"] = syntax_errors

        # Identify strengths
        if results["package_structure"].get("structure_score", 0) > 80:
            summary["strengths"].append("Well-organized package structure")

        if results["code_quality"].get("overall_quality_score", 0) > 0.8:
            summary["strengths"].append("High code quality")

        if results["security"].get("overall_secure", False):
            summary["strengths"].append("No security issues detected")

        if results["tests"].get("total_coverage", 0) > 80:
            summary["strengths"].append("Good test coverage")

        if results["documentation"].get("overall_doc_score", 0) > 80:
            summary["strengths"].append("Comprehensive documentation")

        # Identify weaknesses and priority fixes
        if results["code_quality"].get("syntax_errors"):
            summary["weaknesses"].append("Syntax errors present")
            summary["priority_fixes"].append("Fix all syntax errors")

        if not results["security"].get("overall_secure", True):
            summary["weaknesses"].append("Security vulnerabilities detected")
            summary["priority_fixes"].append("Address security issues")

        if not results["tests"].get("has_tests", False):
            summary["weaknesses"].append("No tests found")
            summary["priority_fixes"].append("Add comprehensive tests")
        elif results["tests"].get("total_coverage", 0) < 70:
            summary["weaknesses"].append("Low test coverage")
            summary["priority_fixes"].append("Increase test coverage")

        if not results["documentation"].get("readme", {}).get("exists", False):
            summary["weaknesses"].append("Missing README")
            summary["priority_fixes"].append("Create comprehensive README")

        return summary

    def _generate_comprehensive_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate comprehensive recommendations for improvement."""
        recommendations = []

        # High priority recommendations (critical issues)
        if results["code_quality"].get("syntax_errors"):
            recommendations.append("🚨 CRITICAL: Fix syntax errors before proceeding")

        if not results["security"].get("overall_secure", True):
            recommendations.append("🚨 CRITICAL: Address security vulnerabilities immediately")

        # Structure recommendations
        structure_score = results["package_structure"].get("structure_score", 0)
        if structure_score < 70:
            recommendations.append("📁 Improve package structure and add missing files")

        # Code quality recommendations
        code_score = results["code_quality"].get("overall_quality_score", 0)
        if code_score < 0.7:
            recommendations.append(
                "🔧 Improve code quality: add type hints, docstrings, and follow PEP 8"
            )

        # Test recommendations
        if not results["tests"].get("has_tests", False):
            recommendations.append("🧪 Add comprehensive test suite with pytest")
        elif results["tests"].get("total_coverage", 0) < 80:
            recommendations.append("📊 Increase test coverage to at least 80%")

        # Documentation recommendations
        doc_score = results["documentation"].get("overall_doc_score", 0)
        if doc_score < 70:
            recommendations.append("📚 Improve documentation: README, docstrings, and API docs")

        # Specific recommendations from sub-validators
        for category in ["package_structure", "code_quality", "security", "tests", "documentation"]:
            if category in results and "recommendations" in results[category]:
                for rec in results[category]["recommendations"][:2]:  # Limit to top 2 per category
                    if rec not in recommendations:
                        recommendations.append(f"💡 {rec}")

        # General recommendations
        if results["overall_score"] < 60:
            recommendations.append(
                "🎯 Focus on fixing critical issues first, then improve incrementally"
            )
        elif results["overall_score"] < 80:
            recommendations.append(
                "⭐ Good foundation! Polish remaining issues for production readiness"
            )
        else:
            recommendations.append(
                "🎉 Excellent quality! Consider advanced optimizations and features"
            )

        return recommendations[:10]  # Limit to top 10 recommendations


# Utility functions for external use
async def validate_package_comprehensive(package_dir: Path, **kwargs) -> Dict[str, Any]:
    """
    Convenience function for comprehensive package validation.

    Args:
        package_dir: Path to package directory
        **kwargs: Additional options for validation

    Returns:
        Dict containing comprehensive validation results
    """
    validator = QualityValidator()
    return await validator.validate_package_quality(package_dir, **kwargs)


def validate_code_syntax(code: str) -> Tuple[bool, List[str]]:
    """
    Convenience function for code syntax validation.

    Args:
        code: Python code to validate

    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = CodeValidator()
    return validator.validate_syntax(code)


def validate_package_structure(package_dir: Path) -> Dict[str, Any]:
    """
    Convenience function for package structure validation.

    Args:
        package_dir: Path to package directory

    Returns:
        Dict containing structure validation results
    """
    validator = PackageValidator()
    return validator.validate_structure(package_dir)
