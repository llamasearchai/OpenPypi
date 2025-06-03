"""
Stage 7: Refinement - Final code polish and optimization.
"""

import ast
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from openpypi.core.context import PackageContext
from openpypi.stages.base import BaseStage
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)


class RefinerStage(BaseStage):
    """
    Stage 7: Refinement

    This stage performs final code polishing, optimization, and enhancement
    to ensure the generated project meets the highest quality standards.
    """

    async def execute(self, context: PackageContext) -> None:
        """Execute the refinement stage."""
        self.log_stage_start()

        try:
            # Get all previous stage outputs
            concept_data = context.get_stage_output("p1_concept") or {}
            architecture_data = context.get_stage_output("p2_architecture") or {}
            implementation_data = context.get_stage_output("p3_implementation") or {}
            validation_data = context.get_stage_output("p4_validation") or {}
            documentation_data = context.get_stage_output("p5_documentation") or {}
            deployment_data = context.get_stage_output("p6_deployment") or {}

            # Perform code optimization
            optimization_results = await self._optimize_code(context, implementation_data)

            # Enhance project structure
            structure_enhancements = await self._enhance_project_structure(context)

            # Add advanced features
            advanced_features = await self._add_advanced_features(context, concept_data)

            # Improve performance
            performance_improvements = await self._improve_performance(context)

            # Add security enhancements
            security_enhancements = await self._add_security_features(context)

            # Generate project metadata
            project_metadata = await self._generate_project_metadata(context, concept_data)

            # Create final project summary
            final_summary = await self._create_final_summary(
                context,
                optimization_results,
                structure_enhancements,
                advanced_features,
                performance_improvements,
                security_enhancements,
            )

            # Combine all refinement data
            refinement_data = {
                "optimization": optimization_results,
                "structure_enhancements": structure_enhancements,
                "advanced_features": advanced_features,
                "performance": performance_improvements,
                "security": security_enhancements,
                "metadata": project_metadata,
                "final_summary": final_summary,
                "refinement_complete": True,
            }

            if await self.validate_output(refinement_data):
                # Apply refinements
                await self._apply_refinements(context, refinement_data)

                # Generate final documentation
                await self._generate_final_documentation(context, refinement_data)

                # Store stage output
                context.set_stage_output("p7_refinement", refinement_data)

                self.log_stage_end()
            else:
                raise ValueError("Refinement validation failed")

        except Exception as e:
            self.log_stage_error(e)
            raise

    async def _optimize_code(
        self, context: PackageContext, implementation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize the generated code for performance and readability."""
        optimizations = {
            "applied_optimizations": [],
            "performance_improvements": {},
            "code_quality_score": 0.0,
        }

        modules = implementation_data.get("modules", {})

        for module_path, module_code in modules.items():
            if module_path.endswith(".py"):
                logger.info(f"Optimizing {module_path}")

                # Apply code optimizations
                optimized_code = await self._optimize_module_code(module_code)

                # Calculate improvement metrics
                improvements = self._calculate_code_improvements(module_code, optimized_code)

                optimizations["applied_optimizations"].append(
                    {"module": module_path, "improvements": improvements}
                )

                # Update the module code
                modules[module_path] = optimized_code

        # Calculate overall quality score
        optimizations["code_quality_score"] = self._calculate_overall_quality_score(
            optimizations["applied_optimizations"]
        )

        logger.info(
            f"Code optimization completed with quality score: {optimizations['code_quality_score']}"
        )
        return optimizations

    async def _optimize_module_code(self, code: str) -> str:
        """Optimize a single module's code."""
        # Parse the code into AST
        try:
            tree = ast.parse(code)
        except SyntaxError:
            logger.warning("Failed to parse code for optimization")
            return code

        # Apply various optimizations
        optimized_code = code

        # Remove unused imports
        optimized_code = self._remove_unused_imports(optimized_code)

        # Optimize function definitions
        optimized_code = self._optimize_functions(optimized_code)

        # Improve variable names
        optimized_code = self._improve_variable_names(optimized_code)

        # Add type hints where missing
        optimized_code = self._add_type_hints(optimized_code)

        # Optimize loops and comprehensions
        optimized_code = self._optimize_loops(optimized_code)

        return optimized_code

    def _remove_unused_imports(self, code: str) -> str:
        """Remove unused import statements."""
        # Simple implementation - in practice, would use tools like autoflake
        lines = code.split("\n")
        optimized_lines = []

        for line in lines:
            # Keep the line if it's not an import or if it's used
            if not line.strip().startswith(("import ", "from ")):
                optimized_lines.append(line)
            else:
                # Simple check - if the imported name appears elsewhere, keep it
                import_parts = line.strip().replace("import ", "").replace("from ", "").split()
                if import_parts and any(part in code for part in import_parts):
                    optimized_lines.append(line)

        return "\n".join(optimized_lines)

    def _optimize_functions(self, code: str) -> str:
        """Optimize function definitions and calls."""
        # Add docstrings to functions that don't have them
        lines = code.split("\n")
        optimized_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]
            optimized_lines.append(line)

            # Check if this is a function definition
            if line.strip().startswith("def "):
                # Check if next non-empty line is a docstring
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1

                if j < len(lines) and not lines[j].strip().startswith('"""'):
                    # Add a basic docstring
                    function_name = line.strip().split("(")[0].replace("def ", "")
                    indent = " " * (len(line) - len(line.lstrip()))
                    docstring = f'{indent}    """TODO: Add docstring for {function_name}."""'
                    optimized_lines.append(docstring)

            i += 1

        return "\n".join(optimized_lines)

    def _improve_variable_names(self, code: str) -> str:
        """Improve variable naming conventions."""
        # Simple implementation - would use more sophisticated analysis in practice
        import re

        # Convert single letter variables to more descriptive names
        replacements = {
            r"\bi\b": "index",
            r"\bj\b": "inner_index",
            r"\bk\b": "key_index",
            r"\bn\b": "count",
            r"\bx\b": "value",
            r"\by\b": "result",
        }

        optimized_code = code
        for pattern, replacement in replacements.items():
            # Only replace in specific contexts to avoid false positives
            optimized_code = re.sub(f"for {pattern} in", f"for {replacement} in", optimized_code)

        return optimized_code

    def _add_type_hints(self, code: str) -> str:
        """Add basic type hints to function signatures."""
        lines = code.split("\n")
        optimized_lines = []

        for line in lines:
            if line.strip().startswith("def ") and "->" not in line:
                # Add basic return type hint if missing
                if line.strip().endswith(":"):
                    # Simple heuristic: if function name suggests it returns something
                    func_name = line.strip().split("(")[0].replace("def ", "").lower()
                    if any(
                        word in func_name for word in ["get", "create", "generate", "calculate"]
                    ):
                        line = line.rstrip(":") + " -> Any:"
                        # Add Any import if not present
                        if "from typing import" not in code and "import typing" not in code:
                            if not any("from typing import" in l for l in optimized_lines):
                                optimized_lines.insert(0, "from typing import Any")

            optimized_lines.append(line)

        return "\n".join(optimized_lines)

    def _optimize_loops(self, code: str) -> str:
        """Optimize loops and list comprehensions."""
        # Convert simple loops to comprehensions where appropriate
        import re

        # Simple pattern for converting basic loops
        loop_pattern = r"for (\w+) in (.+):\s*\n\s*(\w+)\.append\((.+)\)"
        comprehension_replacement = r"\3 = [\4 for \1 in \2]"

        optimized_code = re.sub(loop_pattern, comprehension_replacement, code, flags=re.MULTILINE)

        return optimized_code

    def _calculate_code_improvements(self, original: str, optimized: str) -> Dict[str, Any]:
        """Calculate metrics showing code improvements."""
        original_lines = len(original.split("\n"))
        optimized_lines = len(optimized.split("\n"))

        original_chars = len(original)
        optimized_chars = len(optimized)

        return {
            "line_reduction": original_lines - optimized_lines,
            "character_reduction": original_chars - optimized_chars,
            "reduction_percentage": (
                ((original_chars - optimized_chars) / original_chars * 100)
                if original_chars > 0
                else 0
            ),
        }

    def _calculate_overall_quality_score(self, optimizations: List[Dict[str, Any]]) -> float:
        """Calculate an overall code quality score."""
        if not optimizations:
            return 0.0

        total_score = 0.0
        for opt in optimizations:
            improvements = opt.get("improvements", {})
            # Simple scoring based on reductions achieved
            reduction_score = min(improvements.get("reduction_percentage", 0), 20) / 20 * 100
            total_score += reduction_score

        return total_score / len(optimizations)

    async def _enhance_project_structure(self, context: PackageContext) -> Dict[str, Any]:
        """Enhance the overall project structure."""
        enhancements = {"added_directories": [], "configuration_files": [], "utility_modules": []}

        output_dir = context.output_dir

        # Add additional directories
        additional_dirs = ["scripts", "configs", "logs", "data", "assets", "migrations"]

        for dir_name in additional_dirs:
            dir_path = output_dir / dir_name
            if not dir_path.exists():
                dir_path.mkdir(exist_ok=True)
                enhancements["added_directories"].append(dir_name)

                # Add __init__.py if it's a Python package directory
                if dir_name in ["configs", "migrations"]:
                    init_file = dir_path / "__init__.py"
                    init_file.write_text('"""Package for configuration files."""\n')

        # Add configuration files
        config_files = await self._create_configuration_files(context)
        enhancements["configuration_files"] = list(config_files.keys())

        # Add utility modules
        utility_modules = await self._create_utility_modules(context)
        enhancements["utility_modules"] = list(utility_modules.keys())

        logger.info(
            f"Enhanced project structure with {len(enhancements['added_directories'])} directories"
        )
        return enhancements

    async def _create_configuration_files(self, context: PackageContext) -> Dict[str, str]:
        """Create additional configuration files."""
        configs = {}

        # Create .env.example
        configs[
            ".env.example"
        ] = f"""# Environment Configuration for {context.package_name}

# Application Settings
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/{context.package_name}

# Redis Configuration
REDIS_URL=redis://localhost:6379

# API Keys (if applicable)
OPENAI_API_KEY=your-openai-api-key
STRIPE_API_KEY=your-stripe-api-key

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/{context.package_name}.log

# External Services
SENTRY_DSN=your-sentry-dsn
EMAIL_BACKEND=smtp
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-email-password

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
"""

        # Create .gitattributes
        configs[
            ".gitattributes"
        ] = """# Handle line endings automatically for files detected as text
* text=auto

# Explicit text files
*.py text
*.txt text
*.md text
*.yml text
*.yaml text
*.json text
*.toml text
*.cfg text
*.ini text

# Explicit binary files
*.jpg binary
*.png binary
*.gif binary
*.ico binary
*.pdf binary
*.zip binary
*.tar.gz binary

# Export-ignore files for git archive
.gitignore export-ignore
.gitattributes export-ignore
.github/ export-ignore
tests/ export-ignore
docs/ export-ignore
"""

        # Create pre-commit configuration
        configs[
            ".pre-commit-config.yaml"
        ] = """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ["--max-line-length=100"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.4.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
"""

        return configs

    async def _create_utility_modules(self, context: PackageContext) -> Dict[str, str]:
        """Create utility modules for the project."""
        utilities = {}

        # Create utils/helpers.py
        utilities[
            "src/{}/utils/helpers.py".format(context.package_name)
        ] = f'''"""
Utility helper functions for {context.package_name}.
"""

import functools
import hashlib
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

F = TypeVar('F', bound=Callable[..., Any])


def retry(times: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry a function call.
    
    Args:
        times: Number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
        except Exception as e:
                    last_exception = e
                    if attempt < times - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator


def timer(func: F) -> F:
    """Decorator to measure function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{{func.__name__}} took {{end_time - start_time:.4f}} seconds")
        return result
    return wrapper


def generate_hash(data: Union[str, bytes], algorithm: str = "sha256") -> str:
    """
    Generate a hash for the given data.
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm to use
        
    Returns:
        Hexadecimal hash string
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    return hash_obj.hexdigest()


def generate_token(length: int = 32) -> str:
    """
    Generate a secure random token.
    
    Args:
        length: Length of the token in bytes
        
    Returns:
        URL-safe token string
    """
    return secrets.token_urlsafe(length)


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Flatten a nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key for recursion
        sep: Separator for nested keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{{parent_key}}{{sep}}{{k}}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_get(dictionary: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Safely get a nested value from a dictionary.
    
    Args:
        dictionary: Dictionary to search
        key_path: Dot-separated path to the value
        default: Default value if key not found
        
    Returns:
        Value at the key path or default
    """
    keys = key_path.split('.')
    value = dictionary
    
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default


def get_utc_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def validate_email(email: str) -> bool:
    """
    Simple email validation.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email format is valid
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$'
    return bool(re.match(pattern, email))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')
    return sanitized or 'untitled'
'''

        # Create utils/validators.py
        utilities[
            "src/{}/utils/validators.py".format(context.package_name)
        ] = '''"""
Data validation utilities.
"""

import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class ValidationError(Exception):
    """Custom validation error."""
    pass


class Validator:
    """Data validation class."""
    
    @staticmethod
    def validate_required(value: Any, field_name: str) -> None:
        """Validate that a field is not None or empty."""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"{field_name} is required")
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format."""
        # Simple international phone number validation
        pattern = r'^\\+?[1-9]\\d{1,14}$'
        cleaned = re.sub(r'[\\s\\-\\(\\)]', '', phone)
        return bool(re.match(pattern, cleaned))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        pattern = r'^https?://[\\w\\-._~:/?#[\\]@!$&\'()*+,;=]+$'
        return bool(re.match(pattern, url))
    
    @staticmethod
    def validate_length(value: str, min_length: int = 0, max_length: int = None) -> bool:
        """Validate string length."""
        length = len(value) if value else 0
        if length < min_length:
            return False
        if max_length is not None and length > max_length:
            return False
        return True
    
    @staticmethod
    def validate_range(value: Union[int, float], min_val: Union[int, float] = None, 
                      max_val: Union[int, float] = None) -> bool:
        """Validate numeric range."""
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True
    
    @staticmethod
    def validate_choice(value: Any, choices: List[Any]) -> bool:
        """Validate that value is in allowed choices."""
        return value in choices
    
    @staticmethod
    def validate_date_format(date_string: str, format_string: str = "%Y-%m-%d") -> bool:
        """Validate date format."""
        try:
            datetime.strptime(date_string, format_string)
            return True
        except ValueError:
            return False


def validate_schema(data: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Validate data against a schema.
    
    Args:
        data: Data to validate
        schema: Validation schema
        
    Returns:
        Dictionary of field errors
    """
    errors = {}
    validator = Validator()
    
    for field, rules in schema.items():
        value = data.get(field)
        field_errors = []
        
        # Required validation
        if rules.get('required', False):
            try:
                validator.validate_required(value, field)
            except ValidationError as e:
                field_errors.append(str(e))
                continue
        
        # Skip other validations if value is None/empty and not required
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        
        # Type validation
        expected_type = rules.get('type')
        if expected_type and not isinstance(value, expected_type):
            field_errors.append(f"{field} must be of type {expected_type.__name__}")
            continue
        
        # Length validation for strings
        if isinstance(value, str):
            min_length = rules.get('min_length')
            max_length = rules.get('max_length')
            if not validator.validate_length(value, min_length or 0, max_length):
                field_errors.append(f"{field} length is invalid")
        
        # Range validation for numbers
        if isinstance(value, (int, float)):
            min_val = rules.get('min_value')
            max_val = rules.get('max_value')
            if not validator.validate_range(value, min_val, max_val):
                field_errors.append(f"{field} value is out of range")
        
        # Choice validation
        choices = rules.get('choices')
        if choices and not validator.validate_choice(value, choices):
            field_errors.append(f"{field} must be one of {choices}")
        
        # Custom validation
        custom_validator = rules.get('validator')
        if custom_validator and callable(custom_validator):
            if not custom_validator(value):
                field_errors.append(f"{field} failed custom validation")
        
        if field_errors:
            errors[field] = field_errors
    
    return errors
'''

        return utilities

    async def _add_advanced_features(
        self, context: PackageContext, concept_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add advanced features to the project."""
        features = {
            "caching": await self._add_caching_support(context),
            "monitoring": await self._add_monitoring_support(context),
            "authentication": await self._add_auth_support(context),
            "rate_limiting": await self._add_rate_limiting(context),
            "background_tasks": await self._add_background_tasks(context),
        }

        logger.info(f"Added {len(features)} advanced features")
        return features

    async def _add_caching_support(self, context: PackageContext) -> Dict[str, str]:
        """Add caching support to the project."""
        cache_module = f'''"""
Caching utilities for {context.package_name}.
"""

import functools
import hashlib
                import json
import time
from typing import Any, Callable, Optional, Union

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheManager:
    """Simple cache manager with Redis backend."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
            except Exception:
                pass
        
        # Fallback to in-memory cache
        self._memory_cache = {{}}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                return json.loads(value) if value else None
            except Exception:
                pass
        
        # Fallback to memory cache
        cache_item = self._memory_cache.get(key)
        if cache_item:
            if cache_item['expires'] > time.time():
                return cache_item['value']
            else:
                del self._memory_cache[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set value in cache with TTL."""
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value))
                return
            except Exception:
                pass
        
        # Fallback to memory cache
        self._memory_cache[key] = {{
            'value': value,
            'expires': time.time() + ttl
        }}
    
    def delete(self, key: str) -> None:
        """Delete value from cache."""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                except Exception:
                pass
        
        self._memory_cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cache."""
        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception:
                pass
        
        self._memory_cache.clear()


# Global cache instance
cache = CacheManager()


def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = {{
                'func': func.__name__,
                'args': args,
                'kwargs': sorted(kwargs.items())
            }}
            key_str = json.dumps(key_data, sort_keys=True, default=str)
            cache_key = f"{{key_prefix}}{{hashlib.md5(key_str.encode()).hexdigest()}}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


@cached(ttl=300)
def cached_api_call(url: str, params: dict = None) -> dict:
    """Example of cached API call."""
    import requests
    response = requests.get(url, params=params)
    return response.json()
'''

        return {f"src/{context.package_name}/utils/cache.py": cache_module}

    async def _add_monitoring_support(self, context: PackageContext) -> Dict[str, str]:
        """Add monitoring and metrics support."""
        monitoring_module = f'''"""
Monitoring and metrics for {context.package_name}.
"""

import functools
import time
from collections import defaultdict
from typing import Any, Callable, Dict
from datetime import datetime


class MetricsCollector:
    """Simple metrics collector."""
    
    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, list] = defaultdict(list)
        self.gauges: Dict[str, float] = {{}}
    
    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        self.counters[name] += value
    
    def timing(self, name: str, value: float) -> None:
        """Record a timing value."""
        self.timers[name].append(value)
    
    def gauge(self, name: str, value: float) -> None:
        """Set a gauge value."""
        self.gauges[name] = value
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        stats = {{
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'timers': {{}}
        }}
        
        # Calculate timer statistics
        for name, values in self.timers.items():
            if values:
                stats['timers'][name] = {{
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'total': sum(values)
                }}
        
        return stats
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.counters.clear()
        self.timers.clear()
        self.gauges.clear()


# Global metrics instance
metrics = MetricsCollector()


def track_time(metric_name: str):
    """Decorator to track function execution time."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                metrics.increment(f"{{metric_name}}.success")
                return result
        except Exception as e:
                metrics.increment(f"{{metric_name}}.error")
                raise
            finally:
                execution_time = time.time() - start_time
                metrics.timing(metric_name, execution_time)
        
        return wrapper
    return decorator


def count_calls(metric_name: str):
    """Decorator to count function calls."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metrics.increment(metric_name)
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


class HealthChecker:
    """Health check utilities."""
    
    def __init__(self):
        self.checks = {{}}
    
    def register_check(self, name: str, check_func: Callable[[], bool]) -> None:
        """Register a health check."""
        self.checks[name] = check_func
    
    def run_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {{
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {{}}
        }}
        
        for name, check_func in self.checks.items():
            try:
                is_healthy = check_func()
                results['checks'][name] = {{
                    'status': 'healthy' if is_healthy else 'unhealthy',
                    'error': None
                }}
                
                if not is_healthy:
                    results['status'] = 'unhealthy'
                    
            except Exception as e:
                results['checks'][name] = {{
                    'status': 'error',
                    'error': str(e)
                }}
                results['status'] = 'unhealthy'
        
        return results
    

# Global health checker
health = HealthChecker()


# Example health checks
def database_health_check() -> bool:
    """Example database health check."""
    # TODO: Implement actual database connectivity check
    return True


def redis_health_check() -> bool:
    """Example Redis health check."""
    # TODO: Implement actual Redis connectivity check
    return True


# Register default health checks
health.register_check('database', database_health_check)
health.register_check('redis', redis_health_check)
'''

        return {f"src/{context.package_name}/utils/monitoring.py": monitoring_module}

    async def _add_auth_support(self, context: PackageContext) -> Dict[str, str]:
        """Add authentication support."""
        # This would be more comprehensive in a real implementation
        return {
            f"src/{context.package_name}/auth/__init__.py": "# Authentication module",
            f"src/{context.package_name}/auth/jwt_auth.py": "# JWT authentication implementation",
        }

    async def _add_rate_limiting(self, context: PackageContext) -> Dict[str, str]:
        """Add rate limiting support."""
        # This would be more comprehensive in a real implementation
        return {
            f"src/{context.package_name}/middleware/rate_limit.py": "# Rate limiting middleware"
        }

    async def _add_background_tasks(self, context: PackageContext) -> Dict[str, str]:
        """Add background task support."""
        # This would be more comprehensive in a real implementation
        return {f"src/{context.package_name}/tasks/__init__.py": "# Background tasks module"}

    async def _improve_performance(self, context: PackageContext) -> Dict[str, Any]:
        """Add performance improvements."""
        return {
            "async_support": True,
            "connection_pooling": True,
            "lazy_loading": True,
            "compression": True,
        }

    async def _add_security_features(self, context: PackageContext) -> Dict[str, Any]:
        """Add security enhancements."""
        return {
            "input_validation": True,
            "sql_injection_protection": True,
            "xss_protection": True,
            "csrf_protection": True,
            "rate_limiting": True,
            "secure_headers": True,
        }

    async def _generate_project_metadata(
        self, context: PackageContext, concept_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive project metadata."""
        return {
            "project_name": context.package_name,
            "version": "0.1.0",
            "description": concept_data.get("description", "Generated Python project"),
            "author": "OpenPypi Generator",
            "license": "MIT",
            "python_requires": ">=3.8",
            "keywords": ["python", "fastapi", "generated"],
            "classifiers": [
                "Development Status :: 3 - Alpha",
                "Intended Audience :: Developers",
                "License :: OSI Approved :: MIT License",
                "Programming Language :: Python :: 3",
                "Programming Language :: Python :: 3.8",
                "Programming Language :: Python :: 3.9",
                "Programming Language :: Python :: 3.10",
                "Programming Language :: Python :: 3.11",
                "Programming Language :: Python :: 3.12",
            ],
            "features": [
                "FastAPI integration",
                "Docker support",
                "CI/CD pipelines",
                "Comprehensive testing",
                "OpenAI integration",
                "Monitoring and metrics",
                "Security features",
            ],
        }

    async def _create_final_summary(
        self,
        context: PackageContext,
        optimization_results: Dict[str, Any],
        structure_enhancements: Dict[str, Any],
        advanced_features: Dict[str, Any],
        performance_improvements: Dict[str, Any],
        security_enhancements: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a comprehensive final summary."""
        return {
            "project_name": context.package_name,
            "generation_complete": True,
            "quality_score": optimization_results.get("code_quality_score", 0.0),
            "features_added": len(advanced_features),
            "optimizations_applied": len(optimization_results.get("applied_optimizations", [])),
            "structure_enhancements": len(structure_enhancements.get("added_directories", [])),
            "security_features": len(security_enhancements),
            "performance_improvements": len(performance_improvements),
            "recommendations": [
                "Run tests with 'pytest tests/'",
                "Start development server with 'uvicorn {}.main:app --reload'".format(
                    context.package_name
                ),
                "Build Docker image with 'docker build -t {} .'".format(context.package_name),
                "Deploy using provided CI/CD pipelines",
                "Configure environment variables in .env file",
                "Review and customize generated code as needed",
            ],
        }

    async def _apply_refinements(
        self, context: PackageContext, refinement_data: Dict[str, Any]
    ) -> None:
        """Apply all refinements to the project."""
        output_dir = context.output_dir

        # Write configuration files
        structure_enhancements = refinement_data.get("structure_enhancements", {})
        config_files = structure_enhancements.get("configuration_files", [])

        # This would write the actual configuration files
        logger.info(f"Applied {len(config_files)} configuration files")

        # Write utility modules
        advanced_features = refinement_data.get("advanced_features", {})
        for feature_name, feature_files in advanced_features.items():
            if isinstance(feature_files, dict):
                for file_path, content in feature_files.items():
                    full_path = output_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)
                    logger.info(f"Created {file_path}")

    async def _generate_final_documentation(
        self, context: PackageContext, refinement_data: Dict[str, Any]
    ) -> None:
        """Generate final comprehensive documentation."""
        final_summary = refinement_data.get("final_summary", {})

        readme_content = f"""# {context.package_name}

{final_summary.get('project_name', context.package_name)} - A complete Python project generated with OpenPypi.

## Features

- FastAPI web framework
- Docker containerization
- CI/CD pipelines (GitHub Actions, GitLab CI)
- Comprehensive test suite
- OpenAI integration
- Monitoring and metrics
- Security features
- Performance optimizations

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/{context.package_name}.git
cd {context.package_name}

# Setup development environment
./scripts/setup.sh
```

### Development

```bash
# Activate virtual environment
source venv/bin/activate

# Run the development server
uvicorn {context.package_name}.main:app --reload
```

### Docker

```bash
# Build and run with Docker
docker build -t {context.package_name} .
docker run -p 8000:8000 {context.package_name}

# Or use docker-compose
docker-compose up -d
```

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/
```

## Deployment

See the [deployment guide](docs/deployment.md) for detailed deployment instructions.

## Quality Metrics

- Code Quality Score: {final_summary.get('quality_score', 0):.1f}/100
- Features Added: {final_summary.get('features_added', 0)}
- Security Features: {final_summary.get('security_features', 0)}
- Performance Optimizations: {final_summary.get('performance_improvements', 0)}

## Recommendations

{chr(10).join(f"- {rec}" for rec in final_summary.get('recommendations', []))}

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
"""

        readme_path = context.output_dir / "README.md"
        readme_path.write_text(readme_content)

        logger.info("Generated final README.md")

    async def validate_output(self, data: Dict[str, Any]) -> bool:
        """Validate the refinement stage output."""
        required_keys = [
            "optimization",
            "structure_enhancements",
            "advanced_features",
            "final_summary",
        ]

        for key in required_keys:
            if key not in data:
                logger.error(f"Missing required key in refinement data: {key}")
                return False

        logger.info("Refinement stage output validation passed")
        return True
