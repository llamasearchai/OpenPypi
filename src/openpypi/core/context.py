"""
Package context management for maintaining state across stages.
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PackageContext:
    """
    Context object that maintains state throughout package creation.
    
    This class stores all information needed across the 7 stages of
    package generation, including user inputs, AI responses, and
    generated artifacts.
    """
    
    # User inputs
    idea: str
    output_dir: Path
    author: str = "OpenPypi User"
    email: str = "user@example.com"
    license_type: str = "MIT"
    python_version: str = ">=3.8"
    package_type: str = "library"
    features: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    template: Optional[str] = None
    
    # Generated metadata
    package_name: str = ""
    version: str = "0.1.0"
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)
    
    # Stage outputs
    stage_outputs: Dict[str, Any] = field(default_factory=dict)
    
    # Tracking
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        
        # Generate package name if not set
        if not self.package_name:
            self.package_name = self._generate_package_name()
    
    def _generate_package_name(self) -> str:
        """Generate package name from idea."""
        words = self.idea.lower().split()
        stop_words = {"a", "an", "the", "for", "with", "to", "and", "or", "but"}
        meaningful_words = [w for w in words if w not in stop_words and w.isalpha()]
        
        if not meaningful_words:
            return "ai_package"
        
        package_name = "_".join(meaningful_words[:2])
        # Clean the name
        package_name = "".join(c if c.isalnum() or c == "_" else "_" for c in package_name)
        package_name = package_name.strip("_").lower()
        
        return package_name or "ai_package"
    
    def set_stage_output(self, stage: str, output: Any) -> None:
        """Set output for a specific stage."""
        self.stage_outputs[stage] = output
    
    def get_stage_output(self, stage: str) -> Any:
        """Get output from a specific stage."""
        return self.stage_outputs.get(stage)
    
    def add_dependency(self, dependency: str, dev: bool = False) -> None:
        """Add a dependency to the package."""
        if dev:
            if dependency not in self.dev_dependencies:
                self.dev_dependencies.append(dependency)
        else:
            if dependency not in self.dependencies:
                self.dependencies.append(dependency)
    
    def add_feature(self, feature: str) -> None:
        """Add a feature to the package."""
        if feature not in self.features:
            self.features.append(feature)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        data = asdict(self)
        # Convert Path to string
        data["output_dir"] = str(self.output_dir)
        data["created_at"] = self.created_at.isoformat()
        return data
    
    def save(self, filepath: Optional[Path] = None) -> None:
        """Save context to JSON file."""
        if filepath is None:
            filepath = self.output_dir / ".openpypi_context.json"
        
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: Path) -> "PackageContext":
        """Load context from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        
        # Convert string back to Path
        data["output_dir"] = Path(data["output_dir"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        
        return cls(**data)
    
    def get_package_dir(self) -> Path:
        """Get the main package source directory."""
        return self.output_dir / "src" / self.package_name
    
    def get_tests_dir(self) -> Path:
        """Get the tests directory."""
        return self.output_dir / "tests"
    
    def get_docs_dir(self) -> Path:
        """Get the documentation directory."""
        return self.output_dir / "docs"