# novapilot_core/aci.py # Corrected path in comment

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, List # Added List
from .models import Task, ExecutionResult, AgentCapability # Assuming models.py is in the same directory; Added AgentCapability

class AgentCommunicationInterface(ABC):
    """
    Abstract Base Class defining the interface for agent communication.
    """

    @abstractmethod
    async def send_message(self, target_agent_id: str, message_content: Any, message_type: str = "generic") -> bool:
        """
        Sends a message to a specified agent.

        Args:
            target_agent_id: The unique identifier of the recipient agent.
            message_content: The content of the message (can be any serializable object, e.g., a Task).
            message_type: A string indicating the type of message (e.g., "task_request", "status_update").

        Returns:
            True if the message was sent successfully, False otherwise.
        """
        pass

    @abstractmethod
    async def receive_message(self) -> Optional[Any]:
        """
        Receives a message intended for this agent.
        This might involve polling a queue or handling a callback.

        Returns:
            The received message content, or None if no message is available.
        """
        pass

    @abstractmethod
    async def post_task(self, task: Task) -> bool:
        """
        Posts a new task to a specific agent or a general task pool.
        This is a specialized form of send_message.

        Args:
            task: The Task object to be posted.

        Returns:
            True if the task was posted successfully, False otherwise.
        """
        pass

    @abstractmethod
    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[ExecutionResult]:
        """
        Retrieves the result of a previously posted task.

        Args:
            task_id: The ID of the task for which to retrieve the result.
            timeout: Optional duration in seconds to wait for the result.

        Returns:
            The ExecutionResult object, or None if the result is not available or timed out.
        """
        pass

    @abstractmethod
    def register_event_listener(self, event_type: str, callback: Callable[[Any], None]) -> bool:
        """
        Registers a callback function to be invoked when a specific event type occurs.

        Args:
            event_type: The type of event to listen for (e.g., "code_generated", "test_completed").
            callback: The function to call when the event occurs. It should accept the event data as an argument.

        Returns:
            True if the listener was registered successfully, False otherwise.
        """
        pass

    @abstractmethod
    async def emit_event(self, event_type: str, event_data: Any) -> bool:
        """
        Emits an event to notify other interested agents.

        Args:
            event_type: The type of event being emitted.
            event_data: The data associated with the event.

        Returns:
            True if the event was emitted successfully, False otherwise.
        """
        pass

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """
        A unique identifier for this agent.
        """
        pass

    @abstractmethod
    async def get_capabilities(self) -> List[AgentCapability]:
        """
        Returns a list of capabilities this agent possesses.
        """
        pass
