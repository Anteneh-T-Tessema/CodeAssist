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
    task_type: Optional[str] = None # New field

@dataclass
class FileContext:
    file_path: str
    content: Optional[str] = None
    version: Optional[str] = None # e.g., commit hash, timestamp, or content hash
    editable: bool = True
    # editable: Indicates if the file's content is intended to be modifiable by automated agents.
    # - True (default): Agents that perform code modification (generation, refactoring) can operate on this file.
    # - False: Agents should generally avoid modifying this file. Modification attempts by such agents
    #          should ideally result in a task status indicating failure or precondition not met,
    #          with an appropriate error message (e.g., "File {file_path} is not marked as editable.").
    # This flag can be set based on project conventions (e.g., distinguishing source files from build outputs or vendor libraries),
    # user intent for a specific operation, or to temporarily "lock" files during complex sequences.
    # Read-only agents (e.g., CodeUnderstandingAgent performing analysis) can typically ignore this flag for reading purposes.
    # Enforcement is the responsibility of agents that perform modifications.

@dataclass
class CodeBlock:
    file_path: str
    code: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    language: Optional[str] = None
    is_complete_file_content: bool = False # New field
    # is_complete_file_content: True if this CodeBlock represents the entire content of the file
    #                             at file_path. False if it's a snippet, diff, or partial content.
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_context: Optional[FileContext] = None
    # Convention: If file_context is provided, its file_path should match this CodeBlock's file_path.

@dataclass
class ExecutionResult:
    task_id: str
    status: str  # e.g., success, failure, error
    output: Optional[str] = None
    error_message: Optional[str] = None
    artifacts: List[str] = field(default_factory=list) # Paths to generated files or artifacts
    data: Optional[Dict[str, Any]] = None # Add new optional data field

@dataclass
class UserFeedback:
    session_id: str
    interaction_id: str
    feedback_type: str # e.g., explicit_rating, implicit_correction, clarification
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentCapability:
    capability_id: str # e.g., "generate_python_code", "analyze_python_file"
    task_type: str # A more general type, e.g., "code_generation", "file_analysis", "testing"
    description: str # Human-readable description of the capability
    keywords: List[str] = field(default_factory=list) # Keywords to match against task descriptions
    required_input_keys: List[str] = field(default_factory=list) # New field
    generates_output_keys: List[str] = field(default_factory=list) # New field
    # Future fields could include: input_schema, output_schema, supported_languages, etc.
