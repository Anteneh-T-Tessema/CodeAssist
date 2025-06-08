# windsurf_agents/UserInteractionOrchestratorAgent/orchestrator.py
import asyncio
from typing import Any, Callable, Optional # Added Optional, Any, Callable
from windsurf_core.aci import AgentCommunicationInterface
from windsurf_core.models import Task
from windsurf_core.message_bus import message_bus # Import the global instance

class MockOrchestratorAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus # Use the global instance

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def send_task_to_generator(self, task_description: str):
        task = Task(
            task_id="task_001",
            description=task_description,
            source_agent_id=self.agent_id,
            target_agent_id="codegen_agent_01", # Assuming a target ID
            data={"details": "Generate a hello world function in Python"}
        )
        print(f"[{self.agent_id}] Sending task: {task.description} to codegen_agent_01")
        # Use a specific channel for code generation tasks
        await self._message_bus.publish("code_generation_tasks", task)
        return True

    # Implement other ACI abstract methods with basic stubs for this example
    async def send_message(self, target_agent_id: str, message_content: Any, message_type: str = "generic") -> bool:
        print(f"[{self.agent_id}] send_message called (stub)")
        return True

    async def receive_message(self) -> Optional[Any]:
        print(f"[{self.agent_id}] receive_message called (stub)")
        return None

    async def post_task(self, task: Task) -> bool:
        print(f"[{self.agent_id}] post_task called (stub), using send_task_to_generator for this example")
        if task.target_agent_id == "codegen_agent_01": # Simple routing
             await self._message_bus.publish("code_generation_tasks", task)
             return True
        return False

    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[Task]: # Changed Task | None to Optional[Task]
        print(f"[{self.agent_id}] get_task_result called (stub)")
        return None

    def register_event_listener(self, event_type: str, callback: Callable[[Any], None]) -> bool: # Changed callable to Callable, any to Any
        print(f"[{self.agent_id}] register_event_listener called (stub)")
        # In a real scenario, this would use the message bus's subscribe method
        return True

    async def emit_event(self, event_type: str, event_data: Any) -> bool:
        print(f"[{self.agent_id}] emit_event called (stub)")
        await self._message_bus.publish(event_type, event_data)
        return True
