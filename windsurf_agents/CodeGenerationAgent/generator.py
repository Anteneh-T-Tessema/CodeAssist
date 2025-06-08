# windsurf_agents/CodeGenerationAgent/generator.py
import asyncio
from typing import Optional, Any, Callable, Dict # Ensure Dict is imported

from windsurf_core.aci import AgentCommunicationInterface
from windsurf_core.models import Task, ExecutionResult
from windsurf_core.message_bus import message_bus

class CodeGenerationAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._task_queue: Optional[asyncio.Queue] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received task: {task.description}")
        print(f"[{self.agent_id}] Processing task ID: {task.task_id} from {task.source_agent_id}...")
        await asyncio.sleep(0.5) # Simulate work

        generated_code = None
        error_message = None
        status = "completed"

        # Simple simulation of code generation based on task description
        if "hello world function in python" in task.description.lower():
            generated_code = (
                "def greet():\n"
                "    print(\"Hello, Windsurf!\")\n"
                "\n"
                "greet()"
            )
        elif "sum function" in task.description.lower():
            generated_code = (
                "def sum_two_numbers(a, b):\n"
                "    return a + b\n"
            )
        else:
            status = "failed"
            error_message = "Unsupported code generation request or unclear task description."
            print(f"[{self.agent_id}] Task {task.task_id} failed: {error_message}")


        result_data = ExecutionResult(
            task_id=task.task_id,
            status=status,
            output=generated_code if generated_code else error_message, # Put code or error in output
            error_message=error_message if status == "failed" else None,
            artifacts=[] # Could add file path if code was written to a file
        )

        # Publish result to the orchestrator's result channel
        result_channel = f"task_results_{task.source_agent_id}"
        print(f"[{self.agent_id}] Task {task.task_id} processing finished. Status: {status}. Publishing result to '{result_channel}'.")
        await self._message_bus.publish(result_channel, result_data)

    async def start_listening(self):
        # Renamed from listen_for_tasks for consistency
        self._task_queue = await self._message_bus.subscribe("code_generation_tasks")
        print(f"[{self.agent_id}] Subscribed to 'code_generation_tasks'. Listening...")
        try:
            while True:
                message = await self._task_queue.get()
                if isinstance(message, Task):
                    # Ensure it's a task for this agent or a general broadcast this agent handles
                    if message.target_agent_id == self.agent_id or message.target_agent_id is None:
                         asyncio.create_task(self._process_task(message))
                    else:
                        print(f"[{self.agent_id}] Received task {message.task_id} not targeted for this agent. Ignoring.")
                elif message == "stop_listening": # A way to gracefully stop
                    print(f"[{self.agent_id}] Stop signal received for task listener.")
                    break
                else:
                    print(f"[{self.agent_id}] Received non-Task message on tasks channel: {message}")
                self._task_queue.task_done()
        except Exception as e:
            print(f"[{self.agent_id}] Error in task listener: {e}")
        finally:
            if self._task_queue:
                await self._message_bus.unsubscribe("code_generation_tasks", self._task_queue)
            print(f"[{self.agent_id}] Unsubscribed and stopped listening for tasks.")

    async def stop_listening(self):
        # Signal the task listening loop to stop
        await self._message_bus.publish("code_generation_tasks", "stop_listening")


    # --- ACI Implementation (Stubs - can be filled later if needed) ---
    async def send_message(self, target_agent_id: str, message_content: Any, message_type: str = "generic") -> bool:
        print(f"[{self.agent_id}] send_message called (stub)")
        # Example: await self._message_bus.publish(f"agent_messages_{target_agent_id}", message_content)
        return True

    async def receive_message(self) -> Optional[Any]:
        print(f"[{self.agent_id}] receive_message called (stub - use specific listeners)")
        return None

    async def post_task(self, task: Task) -> bool:
        # This agent primarily receives tasks via its subscribed channel
        print(f"[{self.agent_id}] post_task called (stub) - this agent receives tasks via subscription.")
        if task.target_agent_id == self.agent_id:
            # Optionally, could put into its own queue if not using direct listen_for_tasks
            # For now, just acknowledge if it were to be used.
            print(f"[{self.agent_id}] Task {task.task_id} could be processed if direct posting was primary.")
            return True
        return False

    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[ExecutionResult]:
        print(f"[{self.agent_id}] get_task_result called (stub)")
        # Results are proactively published; direct retrieval by others is not the primary model here.
        return None

    def register_event_listener(self, event_type: str, callback: Callable[[Any], None]) -> bool:
        print(f"[{self.agent_id}] register_event_listener for '{event_type}' (stub)")
        return True

    async def emit_event(self, event_type: str, event_data: Any) -> bool:
        print(f"[{self.agent_id}] Emitting event '{event_type}' (stub)")
        await self._message_bus.publish(event_type, event_data)
        return True
