# windsurf_agents/CodeGenerationAgent/generator.py
import asyncio
from typing import Any, Callable, Optional # Added Optional, Any, Callable
from windsurf_core.aci import AgentCommunicationInterface
from windsurf_core.models import Task, ExecutionResult
from windsurf_core.message_bus import message_bus

class MockCodeGeneratorAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._task_queue: Optional[asyncio.Queue] = None # Changed asyncio.Queue | None to Optional[asyncio.Queue]

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received task: {task.description}")
        print(f"[{self.agent_id}] Processing task ID: {task.task_id} from {task.source_agent_id}...")
        await asyncio.sleep(1) # Simulate work
        result_data = ExecutionResult(
            task_id=task.task_id,
            status="completed",
            output=f"Generated code for: {task.description}",
            artifacts=["path/to/generated_file.py"]
        )
        print(f"[{self.agent_id}] Task {task.task_id} completed. Result: {result_data.output}")
        # In a real scenario, publish this result to a specific channel or send directly
        await self._message_bus.publish(f"task_results_{task.source_agent_id}", result_data)

    async def listen_for_tasks(self):
        self._task_queue = await self._message_bus.subscribe("code_generation_tasks")
        print(f"[{self.agent_id}] Subscribed to 'code_generation_tasks'. Listening...")
        try:
            while True:
                task = await self._task_queue.get()
                if isinstance(task, Task):
                    asyncio.create_task(self._process_task(task))
                elif task == "stop_listening":
                    print(f"[{self.agent_id}] Stop signal received.")
                    break # Indented correctly
                else:
                    print(f"[{self.agent_id}] Received unknown message type: {task}")
        finally:
            if self._task_queue:
                await self._message_bus.unsubscribe("code_generation_tasks", self._task_queue)
            print(f"[{self.agent_id}] Unsubscribed and stopped listening.")

    # Implement other ACI abstract methods with basic stubs
    async def send_message(self, target_agent_id: str, message_content: Any, message_type: str = "generic") -> bool:
        print(f"[{self.agent_id}] send_message called (stub)")
        return True

    async def receive_message(self) -> Optional[Any]:
        print(f"[{self.agent_id}] receive_message called (stub)")
        # This agent uses subscribe for primary message intake
        return None

    async def post_task(self, task: Task) -> bool:
        print(f"[{self.agent_id}] post_task called (stub)")
        return False # This agent primarily receives tasks via subscription

    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[Task]: # Changed Task | None to Optional[Task]
        print(f"[{self.agent_id}] get_task_result called (stub)")
        return None

    def register_event_listener(self, event_type: str, callback: Callable[[Any], None]) -> bool: # Changed callable to Callable, any to Any
        print(f"[{self.agent_id}] register_event_listener called (stub)")
        return True

    async def emit_event(self, event_type: str, event_data: Any) -> bool:
        print(f"[{self.agent_id}] emit_event called (stub)")
        await self._message_bus.publish(event_type, event_data)
        return True
