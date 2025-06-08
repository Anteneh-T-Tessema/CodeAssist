# novapilot_agents/CodeUnderstandingAgent/code_analyzer.py # Corrected path in comment
import asyncio
from typing import Optional, Any, Callable, Dict, List # Ensure List is here
from novapilot_core.aci import AgentCommunicationInterface # Corrected import
from novapilot_core.models import Task, ExecutionResult, AgentCapability # Corrected import
from novapilot_core.message_bus import message_bus # Corrected import

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
        discovery_queue = await self._message_bus.subscribe("system_discovery_channel")

        print(f"[{self.agent_id}] Subscribed to 'code_understanding_tasks' and 'system_discovery_channel'. Listening...")

        async def task_listener_loop():
            try:
                while True:
                    message = await self._task_queue.get()
                    if isinstance(message, Task):
                        if message.target_agent_id == self.agent_id or message.target_agent_id is None:
                            asyncio.create_task(self._process_task(message))
                        else:
                            print(f"[{self.agent_id}] Received task {message.task_id} not for this agent. Ignoring.")
                    elif message == "stop_listening_tasks":
                        print(f"[{self.agent_id}] Stop signal received for task listener.")
                        break
                    else:
                        print(f"[{self.agent_id}] Received non-Task message on tasks channel: {message}")
                    if self._task_queue: self._task_queue.task_done()
            finally:
                if self._task_queue:
                    await self._message_bus.unsubscribe("code_understanding_tasks", self._task_queue)
                print(f"[{self.agent_id}] Unsubscribed and stopped listening for tasks.")

        async def discovery_listener_loop():
            try:
                while True:
                    message = await discovery_queue.get()
                    if isinstance(message, dict) and message.get("type") == "request_capabilities":
                        response_channel = message.get("response_channel")
                        if response_channel:
                            print(f"[{self.agent_id}] Received capability request. Responding on {response_channel}.")
                            capabilities = await self.get_capabilities()
                            # capabilities_data = [vars(cap) for cap in capabilities] # If dicts needed
                            capabilities_data = capabilities # Assuming objects are fine
                            await self._message_bus.publish(response_channel, {
                                "type": "agent_capabilities_response",
                                "agent_id": self.agent_id,
                                "capabilities": capabilities_data
                            })
                    elif message == "stop_listening_discovery_system":
                        print(f"[{self.agent_id}] Stop signal received for system discovery listener.")
                        break
                    if discovery_queue: discovery_queue.task_done()
            finally:
                if discovery_queue:
                    await self._message_bus.unsubscribe("system_discovery_channel", discovery_queue)
                print(f"[{self.agent_id}] Unsubscribed and stopped listening on system_discovery_channel.")

        self._listener_tasks = [
            asyncio.create_task(task_listener_loop()),
            asyncio.create_task(discovery_listener_loop())
        ]

    async def stop_listening(self):
        print(f"[{self.agent_id}] Requesting to stop listening.")
        await self._message_bus.publish("code_understanding_tasks", "stop_listening_tasks")
        await self._message_bus.publish("system_discovery_channel", "stop_listening_discovery_system")
        if hasattr(self, '_listener_tasks') and self._listener_tasks:
            await asyncio.gather(*self._listener_tasks, return_exceptions=True)
            print(f"[{self.agent_id}] All listener tasks gathered.")

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

    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                capability_id="analyze_file_line_count",
                task_type="file_analysis_line_count", # Made task_type more specific
                description="Reads a specified file and counts the number of lines.",
                keywords=["read", "analyze", "file", "count", "lines", "length"],
                required_input_keys=["file_path"], # Explicitly requires 'file_path' in Task.data
                generates_output_keys=["line_count", "file_path"] # Output keys in ExecutionResult.data
            )
        ]
