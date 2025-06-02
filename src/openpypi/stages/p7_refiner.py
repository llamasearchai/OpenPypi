if (node.body and
                            isinstance(node.body[0], ast.Expr) and
                            isinstance(node.body[0].value, ast.Constant) and
                            isinstance(node.body[0].value.value, str)):
                            documented_items += 1
            except Exception as e:
                logger.warning(f"Failed to analyze docstrings for {py_file}: {e}")
        
        return (documented_items / total_items * 100) if total_items > 0 else 0.0
    
    def _calculate_code_quality_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall code quality score."""
        score = 100.0
        
        # Deduct for syntax errors (critical)
        score -= len(results["syntax_errors"]) * 20
        
        # Deduct for style violations
        score -= min(len(results["style_violations"]) * 2, 30)
        
        # Deduct for complexity issues
        score -= min(len(results["complexity_issues"]) * 5, 25)
        
        # Bonus for type coverage
        score += (results["type_coverage"] - 50) * 0.2
        
        # Bonus for docstring coverage
        score += (results["docstring_coverage"] - 50) * 0.1
        
        return max(0.0, min(100.0, score))
    
    async def _validate_test_quality(self, context: PackageContext) -> Dict[str, Any]:
        """Validate test quality and coverage."""
        results = {
            "test_files": [],
            "coverage_percentage": 0.0,
            "test_results": {},
            "missing_tests": [],
            "overall_score": 0.0
        }
        
        # Find test files
        test_dirs = ["tests", "test"]
        for test_dir_name in test_dirs:
            test_dir = context.output_dir / test_dir_name
            if test_dir.exists():
                results["test_files"].extend([
                    str(f.relative_to(context.output_dir))
                    for f in test_dir.rglob("test_*.py")
                ])
        
        # Run tests with coverage
        try:
            test_result = subprocess.run(
                ["python", "-m", "pytest", "--cov", context.package_name, "--cov-report=json"],
                capture_output=True,
                text=True,
                cwd=context.output_dir
            )
            
            results["test_results"] = {
                "returncode": test_result.returncode,
                "stdout": test_result.stdout,
                "stderr": test_result.stderr
            }
            
            # Parse coverage report
            coverage_file = context.output_dir / "coverage.json"
            if coverage_file.exists():
                import json
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    results["coverage_percentage"] = coverage_data.get("totals", {}).get("percent_covered", 0)
        
        except Exception as e:
            logger.warning(f"Failed to run tests: {e}")
        
        # Check for missing tests
        results["missing_tests"] = await self._find_missing_tests(context)
        
        # Calculate test quality score
        results["overall_score"] = self._calculate_test_quality_score(results)
        
        return results
    
    async def _find_missing_tests(self, context: PackageContext) -> List[str]:
        """Find modules/functions that lack tests."""
        missing_tests = []
        
        src_dir = context.output_dir / "src" / context.package_name
        test_dirs = [context.output_dir / "tests", context.output_dir / "test"]
        
        if not src_dir.exists():
            return missing_tests
        
        # Get all source modules
        source_modules = []
        for py_file in src_dir.rglob("*.py"):
            if py_file.name != "__init__.py":
                module_name = py_file.stem
                source_modules.append(module_name)
        
        # Check if each module has corresponding tests
        for module in source_modules:
            has_test = False
            for test_dir in test_dirs:
                if test_dir.exists():
                    test_file = test_dir / f"test_{module}.py"
                    if test_file.exists():
                        has_test = True
                        break
            
            if not has_test:
                missing_tests.append(module)
        
        return missing_tests
    
    def _calculate_test_quality_score(self, results: Dict[str, Any]) -> float:
        """Calculate test quality score."""
        score = 0.0
        
        # Base score from coverage
        score += results["coverage_percentage"] * 0.6
        
        # Bonus for having test files
        if results["test_files"]:
            score += 20
        
        # Deduct for missing tests
        score -= len(results["missing_tests"]) * 5
        
        # Bonus if tests pass
        if results["test_results"].get("returncode") == 0:
            score += 20
        
        return max(0.0, min(100.0, score))
    
    async def _validate_documentation(self, context: PackageContext) -> Dict[str, Any]:
        """Validate documentation quality."""
        results = {
            "readme_score": 0.0,
            "api_docs_score": 0.0,
            "sphinx_build": False,
            "missing_sections": [],
            "overall_score": 0.0
        }
        
        # Validate README
        readme_path = context.output_dir / "README.md"
        if readme_path.exists():
            results["readme_score"] = await self._score_readme(readme_path)
        
        # Validate API documentation
        results["api_docs_score"] = await self._score_api_docs(context)
        
        # Check Sphinx build
        docs_dir = context.output_dir / "docs"
        if docs_dir.exists():
            try:
                sphinx_result = subprocess.run(
                    ["make", "html"],
                    capture_output=True,
                    text=True,
                    cwd=docs_dir
                )
                results["sphinx_build"] = sphinx_result.returncode == 0
            except Exception:
                results["sphinx_build"] = False
        
        # Calculate overall documentation score
        results["overall_score"] = (
            results["readme_score"] * 0.4 +
            results["api_docs_score"] * 0.4 +
            (20 if results["sphinx_build"] else 0)
        )
        
        return results
    
    async def _score_readme(self, readme_path: Path) -> float:
        """Score README quality."""
        content = readme_path.read_text(encoding='utf-8')
        score = 0.0
        
        required_sections = [
            "installation", "usage", "features", "api", "contributing", "license"
        ]
        
        for section in required_sections:
            if section.lower() in content.lower():
                score += 100 / len(required_sections)
        
        # Bonus for badges
        if "![" in content or "[![" in content:
            score += 10
        
        # Bonus for code examples
        if "```" in content:
            score += 10
        
        return min(100.0, score)
    
    async def _score_api_docs(self, context: PackageContext) -> float:
        """Score API documentation quality."""
        src_dir = context.output_dir / "src" / context.package_name
        if not src_dir.exists():
            return 0.0
        
        total_functions = 0
        documented_functions = 0
        
        for py_file in src_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not node.name.startswith('_'):  # Only public functions
                            total_functions += 1
                            
                            # Check for docstring
                            if (node.body and
                                isinstance(node.body[0], ast.Expr) and
                                isinstance(node.body[0].value, ast.Constant) and
                                isinstance(node.body[0].value.value, str)):
                                documented_functions += 1
            except Exception:
                continue
        
        return (documented_functions / total_functions * 100) if total_functions > 0 else 0.0
    
    async def _validate_security(self, context: PackageContext) -> Dict[str, Any]:
        """Validate security aspects."""
        results = {
            "bandit_issues": [],
            "dependency_vulnerabilities": [],
            "secret_exposures": [],
            "overall_score": 100.0
        }
        
        # Run Bandit security scan
        try:
            bandit_result = subprocess.run(
                ["bandit", "-r", "src", "-f", "json"],
                capture_output=True,
                text=True,
                cwd=context.output_dir
            )
            
            if bandit_result.stdout:
                import json
                bandit_data = json.loads(bandit_result.stdout)
                results["bandit_issues"] = bandit_data.get("results", [])
        except Exception as e:
            logger.warning(f"Failed to run Bandit: {e}")
        
        # Check for dependency vulnerabilities
        try:
            safety_result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                cwd=context.output_dir
            )
            
            if safety_result.stdout:
                import json
                safety_data = json.loads(safety_result.stdout)
                results["dependency_vulnerabilities"] = safety_data if isinstance(safety_data, list) else []
        except Exception as e:
            logger.warning(f"Failed to run Safety: {e}")
        
        # Check for exposed secrets
        results["secret_exposures"] = await self._check_for_secrets(context)
        
        # Calculate security score
        results["overall_score"] = self._calculate_security_score(results)
        
        return results
    
    async def _check_for_secrets(self, context: PackageContext) -> List[Dict[str, Any]]:
        """Check for exposed secrets in code."""
        import re
        
        secret_patterns = [
            (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?[a-zA-Z0-9]{20,}['\"]?", "API Key"),
            (r"(?i)(secret[_-]?key|secretkey)\s*[:=]\s*['\"]?[a-zA-Z0-9]{20,}['\"]?", "Secret Key"),
            (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?[a-zA-Z0-9]{8,}['\"]?", "Password"),
            (r"sk-[a-zA-Z0-9]{48}", "OpenAI API Key"),
        ]
        
        exposures = []
        src_dir = context.output_dir / "src"
        
        if src_dir.exists():
            for py_file in src_dir.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding='utf-8')
                    
                    for pattern, secret_type in secret_patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            exposures.append({
                                "file": str(py_file.relative_to(context.output_dir)),
                                "type": secret_type,
                                "matches": len(matches)
                            })
                except Exception:
                    continue
        
        return exposures
    
    def _calculate_security_score(self, results: Dict[str, Any]) -> float:
        """Calculate security score."""
        score = 100.0
        
        # Deduct for Bandit issues
        high_severity_issues = [
            issue for issue in results["bandit_issues"]
            if issue.get("issue_severity") == "HIGH"
        ]
        score -= len(high_severity_issues) * 20
        score -= len(results["bandit_issues"]) * 5
        
        # Deduct for dependency vulnerabilities
        score -= len(results["dependency_vulnerabilities"]) * 15
        
        # Deduct for secret exposures
        score -= len(results["secret_exposures"]) * 25
        
        return max(0.0, score)
    
    async def _validate_performance(self, context: PackageContext) -> Dict[str, Any]:
        """Validate performance characteristics."""
        results = {
            "import_time": 0.0,
            "package_size": 0,
            "dependency_count": 0,
            "overall_score": 100.0
        }
        
        # Measure import time
        try:
            import_test = subprocess.run(
                ["python", "-c", f"import time; start=time.time(); import {context.package_name}; print(time.time()-start)"],
                capture_output=True,
                text=True,
                cwd=context.output_dir
            )
            
            if import_test.returncode == 0:
                results["import_time"] = float(import_test.stdout.strip())
        except Exception as e:
            logger.warning(f"Failed to measure import time: {e}")
        
        # Calculate package size
        src_dir = context.output_dir / "src"
        if src_dir.exists():
            total_size = sum(f.stat().st_size for f in src_dir.rglob("*") if f.is_file())
            results["package_size"] = total_size
        
        # Count dependencies
        requirements_file = context.output_dir / "requirements.txt"
        if requirements_file.exists():
            content = requirements_file.read_text()
            deps = [line.strip() for line in content.split('\n') 
                   if line.strip() and not line.startswith('#')]
            results["dependency_count"] = len(deps)
        
        # Calculate performance score
        results["overall_score"] = self._calculate_performance_score(results)
        
        return results
    
    def _calculate_performance_score(self, results: Dict[str, Any]) -> float:
        """Calculate performance score."""
        score = 100.0
        
        # Deduct for slow import time
        if results["import_time"] > 1.0:
            score -= (results["import_time"] - 1.0) * 20
        
        # Deduct for large package size (>10MB)
        if results["package_size"] > 10 * 1024 * 1024:
            score -= 20
        
        # Deduct for too many dependencies
        if results["dependency_count"] > 20:
            score -= (results["dependency_count"] - 20) * 2
        
        return max(0.0, score)
    
    async def _validate_package_structure(self, context: PackageContext) -> Dict[str, Any]:
        """Validate package structure and organization."""
        results = {
            "required_files": {},
            "structure_score": 0.0,
            "recommendations": []
        }
        
        required_files = {
            "README.md": context.output_dir / "README.md",
            "LICENSE": context.output_dir / "LICENSE",
            "pyproject.toml": context.output_dir / "pyproject.toml",
            "setup.py": context.output_dir / "setup.py",
            ".gitignore": context.output_dir / ".gitignore",
            "requirements.txt": context.output_dir / "requirements.txt",
        }
        
        # Check required files
        for file_name, file_path in required_files.items():
            results["required_files"][file_name] = {
                "exists": file_path.exists(),
                "size": file_path.stat().st_size if file_path.exists() else 0
            }
        
        # Check package structure
        src_dir = context.output_dir / "src" / context.package_name
        test_dir = context.output_dir / "tests"
        docs_dir = context.output_dir / "docs"
        
        structure_checks = {
            "has_src_layout": src_dir.exists(),
            "has_tests": test_dir.exists(),
            "has_docs": docs_dir.exists(),
            "has_init_file": (src_dir / "__init__.py").exists() if src_dir.exists() else False,
            "has_main_module": (src_dir / "__main__.py").exists() if src_dir.exists() else False,
        }
        
        # Calculate structure score
        total_checks = len(required_files) + len(structure_checks)
        passed_checks = (
            sum(1 for f in results["required_files"].values() if f["exists"]) +
            sum(1 for check in structure_checks.values() if check)
        )
        
        results["structure_score"] = (passed_checks / total_checks) * 100
        
        # Generate recommendations
        if not structure_checks["has_src_layout"]:
            results["recommendations"].append({
                "category": "Structure",
                "priority": "High",
                "issue": "Missing src/ layout",
                "action": "Consider using src/ layout for better package organization"
            })
        
        if not structure_checks["has_tests"]:
            results["recommendations"].append({
                "category": "Testing",
                "priority": "High",
                "issue": "Missing tests directory",
                "action": "Add tests/ directory with comprehensive test suite"
            })
        
        if not structure_checks["has_docs"]:
            results["recommendations"].append({
                "category": "Documentation",
                "priority": "Medium",
                "issue": "Missing documentation",
                "action": "Add docs/ directory with Sphinx documentation"
            })
        
        return results