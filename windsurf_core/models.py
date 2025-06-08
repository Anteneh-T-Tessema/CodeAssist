# windsurf_core/models.py

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class Task:
    task_id: str
    description: str
    source_agent_id: Optional[str] = None
    target_agent_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # e.g., pending, in_progress, completed, failed
    priority: int = 0 # Higher number means higher priority

@dataclass
class FileContext:
    file_path: str
    content: Optional[str] = None
    version: Optional[str] = None # e.g., commit hash, timestamp
    editable: bool = True

@dataclass
class CodeBlock:
    file_path: str
    code: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    language: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict) # For syntax checks, AST nodes, etc.

@dataclass
class ExecutionResult:
    task_id: str
    status: str  # e.g., success, failure, error
    output: Optional[str] = None
    error_message: Optional[str] = None
    artifacts: List[str] = field(default_factory=list) # Paths to generated files or artifacts

@dataclass
class UserFeedback:
    session_id: str
    interaction_id: str
    feedback_type: str # e.g., explicit_rating, implicit_correction, clarification
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
