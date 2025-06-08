# windsurf_core/__init__.py

from .models import Task, FileContext, CodeBlock, ExecutionResult, UserFeedback
from .aci import AgentCommunicationInterface
from .message_bus import MessageBus, message_bus

__all__ = [
    "Task",
    "FileContext",
    "CodeBlock",
    "ExecutionResult",
    "UserFeedback",
    "AgentCommunicationInterface",
    "MessageBus",
    "message_bus", # Exporting the global instance
]
