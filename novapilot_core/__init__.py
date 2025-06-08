# novapilot_core/__init__.py # Corrected path in comment

from .models import (
    Task, FileContext, CodeBlock, ExecutionResult, UserFeedback, AgentCapability,
    ProjectContext # Add ProjectContext
)
from .aci import AgentCommunicationInterface
from .message_bus import MessageBus, message_bus

__all__ = [
    "Task",
    "FileContext",
    "CodeBlock",
    "ExecutionResult",
    "UserFeedback",
    "AgentCapability",
    "ProjectContext", # Add ProjectContext
    "AgentCommunicationInterface",
    "MessageBus",
    "message_bus", # Exporting the global instance
]
