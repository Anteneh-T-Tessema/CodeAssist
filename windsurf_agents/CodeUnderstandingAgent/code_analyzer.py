# windsurf_agents/CodeUnderstandingAgent/code_analyzer.py
import asyncio
from typing import Optional, Any, Callable, Dict

from windsurf_core.aci import AgentCommunicationInterface
from windsurf_core.models import Task, ExecutionResult
from windsurf_core.message_bus import message_bus

class CodeUnderstandingAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._task_queue: Optional[asyncio.Queue] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received task: {task.description}")
        file_path = task.data.get("file_path")

        if not file_path:
            error_message = "Task data missing 'file_path'."
            print(f"[{self.agent_id}] Task {task.task_id} failed: {error_message}")
            result_data = ExecutionResult(
                task_id=task.task_id,
                status="failed",
                output=error_message,
                error_message=error_message
            )
        else:
            print(f"[{self.agent_id}] Processing file reading for: {file_path}")
            try:
                # In a real scenario, file access should be carefully sandboxed
                # or restricted, especially if file_path can be arbitrary.
                # For this example, we assume direct access is permissible.
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines() # More accurate than counting '\n'
                    line_count = len(lines)

                output_message = f"Successfully read file: {file_path}. Line count: {line_count}."
                print(f"[{self.agent_id}] {output_message}")
                result_data = ExecutionResult(
                    task_id=task.task_id,
                    status="completed",
                    output=output_message,
                    data={"file_path": file_path, "line_count": line_count}
                )
            except FileNotFoundError:
                error_message = f"File not found: {file_path}"
                print(f"[{self.agent_id}] Task {task.task_id} failed: {error_message}")
                result_data = ExecutionResult(
                    task_id=task.task_id,
                    status="failed",
                    output=error_message,
                    error_message=error_message,
                    data={"file_path": file_path}
                )
            except Exception as e:
                error_message = f"An error occurred while reading file {file_path}: {str(e)}"
                print(f"[{self.agent_id}] Task {task.task_id} failed: {error_message}")
                result_data = ExecutionResult(
                    task_id=task.task_id,
                    status="failed",
                    output=error_message,
                    error_message=error_message,
                    data={"file_path": file_path}
                )

        if task.source_agent_id:
            result_channel = f"task_results_{task.source_agent_id}"
            print(f"[{self.agent_id}] Publishing result for task {task.task_id} to '{result_channel}'.")
            await self._message_bus.publish(result_channel, result_data)
        else:
            print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id. Cannot publish result.")

    async def start_listening(self):
        self._task_queue = await self._message_bus.subscribe("code_understanding_tasks")
        print(f"[{self.agent_id}] Subscribed to 'code_understanding_tasks'. Listening...")
        try:
            while True:
                message = await self._task_queue.get()
                if isinstance(message, Task):
                    if message.target_agent_id == self.agent_id or message.target_agent_id is None:
                        asyncio.create_task(self._process_task(message))
                    else:
                        print(f"[{self.agent_id}] Received task {message.task_id} not targeted for this agent. Ignoring.")
                elif message == "stop_listening":
                    print(f"[{self.agent_id}] Stop signal received for task listener.")
                    break
                else:
                    print(f"[{self.agent_id}] Received non-Task message on tasks channel: {message}")
                if self._task_queue: # Check if queue still exists
                    self._task_queue.task_done()
        except Exception as e:
            print(f"[{self.agent_id}] Error in task listener: {e}")
        finally:
            if self._task_queue:
                await self._message_bus.unsubscribe("code_understanding_tasks", self._task_queue)
            print(f"[{self.agent_id}] Unsubscribed and stopped listening for code understanding tasks.")

    async def stop_listening(self):
        print(f"[{self.agent_id}] Requesting to stop listening for tasks.")
        await self._message_bus.publish("code_understanding_tasks", "stop_listening")

    # --- ACI Implementation (Stubs) ---
    async def send_message(self, target_agent_id: str, message_content: Any, message_type: str = "generic") -> bool:
        print(f"[{self.agent_id}] send_message called (stub)")
        return True

    async def receive_message(self) -> Optional[Any]:
        print(f"[{self.agent_id}] receive_message called (stub)")
        return None

    async def post_task(self, task: Task) -> bool:
        print(f"[{self.agent_id}] post_task called (stub)")
        return False

    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[ExecutionResult]:
        print(f"[{self.agent_id}] get_task_result called (stub)")
        return None

    def register_event_listener(self, event_type: str, callback: Callable[[Any], None]) -> bool:
        print(f"[{self.agent_id}] register_event_listener for '{event_type}' (stub)")
        return True

    async def emit_event(self, event_type: str, event_data: Any) -> bool:
        print(f"[{self.agent_id}] Emitting event '{event_type}' (stub)")
        return True
