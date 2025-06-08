# novapilot_agents/CodeUnderstandingAgent/code_analyzer.py
import asyncio
import os # For os.path.join and os.path.isabs
import uuid # For generating unique response channel IDs
from typing import Optional, Any, Callable, Dict, List
from novapilot_core.aci import AgentCommunicationInterface
from novapilot_core.models import Task, ExecutionResult, AgentCapability, ProjectContext # Add ProjectContext
from novapilot_core.message_bus import message_bus

class CodeUnderstandingAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._task_queue: Optional[asyncio.Queue] = None
        self._project_context_cache: Optional[ProjectContext] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def _get_project_context(self) -> Optional[ProjectContext]:
        if self._project_context_cache:
            return self._project_context_cache

        request_id = str(uuid.uuid4())
        response_channel = f"agent_context_response_{self.agent_id}_{request_id}"

        context_response_queue = None
        try:
            context_response_queue = await self._message_bus.subscribe(response_channel)

            request_message = {
                "type": "get_project_context",
                "response_channel": response_channel
            }
            print(f"[{self.agent_id}] Requesting ProjectContext on 'context_requests'. Expecting response on '{response_channel}'.")
            await self._message_bus.publish("context_requests", request_message)

            # Wait for the response with a timeout
            try:
                # Using asyncio.wait_for to handle potential timeouts
                project_context_response = await asyncio.wait_for(context_response_queue.get(), timeout=5.0) # 5s timeout
                if isinstance(project_context_response, ProjectContext):
                    self._project_context_cache = project_context_response
                    print(f"[{self.agent_id}] Received and cached ProjectContext: {self._project_context_cache.project_id}")
                    return self._project_context_cache
                else:
                    print(f"[{self.agent_id}] Received unexpected response type for ProjectContext: {type(project_context_response)}")
                    return None
            except asyncio.TimeoutError:
                print(f"[{self.agent_id}] Timed out waiting for ProjectContext response on '{response_channel}'.")
                return None
            finally:
                # Unsubscribe from the temporary response channel
                if context_response_queue: # Check if it was successfully created
                    await self._message_bus.unsubscribe(response_channel, context_response_queue)
                    print(f"[{self.agent_id}] Unsubscribed from temporary context response channel '{response_channel}'.")

        except Exception as e:
            print(f"[{self.agent_id}] Error during _get_project_context: {e}")
            # Ensure unsubscription if an error occurred before timeout block's finally
            if context_response_queue and response_channel: # Check again before unsubscribing
                 try:
                     await self._message_bus.unsubscribe(response_channel, context_response_queue)
                     print(f"[{self.agent_id}] Unsubscribed from temporary context response channel '{response_channel}' due to exception.")
                 except Exception as unsub_e:
                     print(f"[{self.agent_id}] Error unsubscribing from '{response_channel}': {unsub_e}")
            return None

    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received task: {task.description}")

        project_context = await self._get_project_context()
        original_file_path = task.data.get("file_path")
        resolved_file_path = original_file_path # Default to original

        if not original_file_path:
            error_message = "Task data missing 'file_path'."
            print(f"[{self.agent_id}] Task {task.task_id} failed: {error_message}")
            result_data = ExecutionResult(
                task_id=task.task_id, status="failed", output=error_message, error_message=error_message
            )
        else:
            if project_context and project_context.root_path:
                if not os.path.isabs(original_file_path):
                    resolved_file_path = os.path.join(project_context.root_path, original_file_path)
                    print(f"[{self.agent_id}] Resolved relative path '{original_file_path}' to '{resolved_file_path}' using ProjectContext root '{project_context.root_path}'.")
                # If original_file_path is already absolute, resolved_file_path remains original_file_path (now absolute)
            elif not project_context:
                 print(f"[{self.agent_id}] Warning: ProjectContext not available. Assuming '{original_file_path}' is absolute or accessible directly.")
            # If project_context is available but no root_path (should not happen with current init), treat as no context.

            print(f"[{self.agent_id}] Processing file reading for: {resolved_file_path}")
            try:
                with open(resolved_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                    line_count = len(lines)

                output_message = f"Successfully read file: {resolved_file_path}. Line count: {line_count}."
                print(f"[{self.agent_id}] {output_message}")
                result_data = ExecutionResult(
                    task_id=task.task_id,
                    status="completed",
                    output=output_message,
                    data={"file_path": resolved_file_path, "original_file_path": original_file_path, "line_count": line_count}
                )
            except FileNotFoundError:
                error_message = f"File not found: {resolved_file_path}"
                print(f"[{self.agent_id}] Task {task.task_id} failed: {error_message}")
                result_data = ExecutionResult(
                    task_id=task.task_id,
                    status="failed",
                    output=error_message,
                    error_message=error_message,
                    data={"file_path": resolved_file_path, "original_file_path": original_file_path}
                )
            except Exception as e:
                error_message = f"An error occurred while reading file {resolved_file_path}: {str(e)}"
                print(f"[{self.agent_id}] Task {task.task_id} failed: {error_message}")
                result_data = ExecutionResult(
                    task_id=task.task_id,
                    status="failed",
                    output=error_message,
                    error_message=error_message,
                    data={"file_path": resolved_file_path, "original_file_path": original_file_path}
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
