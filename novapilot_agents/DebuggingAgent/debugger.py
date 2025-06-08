# novapilot_agents/DebuggingAgent/debugger.py
import asyncio
import os # For os.path.join and os.path.isabs
import uuid # For generating unique response channel IDs
from typing import Optional, Any, Callable, Dict, List

from novapilot_core.aci import AgentCommunicationInterface
from novapilot_core.models import Task, ExecutionResult, AgentCapability, ProjectContext
from novapilot_core.message_bus import message_bus

class DebuggingAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._task_queue: Optional[asyncio.Queue] = None
        self._discovery_queue: Optional[asyncio.Queue] = None
        self._listener_tasks: List[asyncio.Task] = []
        self._project_context_cache: Optional[ProjectContext] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def _get_project_context(self) -> Optional[ProjectContext]:
        if self._project_context_cache: # self._project_context_cache should be initialized in __init__
            return self._project_context_cache

        request_id = str(uuid.uuid4())
        # Ensure self.agent_id is available (it's a property)
        response_channel = f"agent_context_response_{self.agent_id}_{request_id}"

        context_response_queue = None
        try:
            context_response_queue = await self._message_bus.subscribe(response_channel)

            request_message = {
                "type": "get_project_context",
                "response_channel": response_channel
            }
            # Ensure self._message_bus is available
            print(f"[{self.agent_id}] Requesting ProjectContext on 'context_requests'. Expecting response on '{response_channel}'.")
            await self._message_bus.publish("context_requests", request_message)

            try:
                project_context_response = await asyncio.wait_for(context_response_queue.get(), timeout=5.0)
                if isinstance(project_context_response, ProjectContext):
                    self._project_context_cache = project_context_response
                    print(f"[{self.agent_id}] Received and cached ProjectContext: ID={self._project_context_cache.project_id if self._project_context_cache else 'N/A'}")
                    return self._project_context_cache
                else:
                    print(f"[{self.agent_id}] Received unexpected response type for ProjectContext: {type(project_context_response)}")
                    return None
            except asyncio.TimeoutError:
                print(f"[{self.agent_id}] Timed out waiting for ProjectContext response on '{response_channel}'.")
                return None
            finally:
                if context_response_queue:
                    await self._message_bus.unsubscribe(response_channel, context_response_queue)
                    print(f"[{self.agent_id}] Unsubscribed from temporary context response channel '{response_channel}'.")

        except Exception as e:
            print(f"[{self.agent_id}] Error during _get_project_context: {e}")
            if context_response_queue and response_channel:
                 try:
                     await self._message_bus.unsubscribe(response_channel, context_response_queue)
                     print(f"[{self.agent_id}] Unsubscribed from temporary context response channel '{response_channel}' due to exception.")
                 except Exception as unsub_e:
                     print(f"[{self.agent_id}] Error unsubscribing from '{response_channel}': {unsub_e}")
            return None

    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received Debugging task: {task.description}, Type: {task.task_type}, Data: {task.data}")

        original_file_path = task.data.get("file_path")
        resolved_file_path = original_file_path # Default to original
        findings_summary = ""
        status = "completed" # Default to completed, as the "act of debugging" (even if just a check) is done.
        result_data_content = {
            "debug_session_id": f"debug_session_{task.task_id}", # Example session ID
            "original_file_path": original_file_path
        }

        if not original_file_path:
            status = "failed"
            output_message = "Missing 'file_path' in task data for debugging."
            result_data_content["error"] = output_message
            print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")
        else:
            project_context = await self._get_project_context()
            if project_context and project_context.root_path:
                if not os.path.isabs(original_file_path):
                    resolved_file_path = os.path.join(project_context.root_path, original_file_path)
                    print(f"[{self.agent_id}] Resolved relative path '{original_file_path}' to '{resolved_file_path}'.")
            elif not project_context:
                print(f"[{self.agent_id}] Warning: ProjectContext not available for task {task.task_id}. Assuming '{original_file_path}' is absolute or directly accessible.")

            result_data_content["resolved_file_path"] = resolved_file_path
            print(f"[{self.agent_id}] Checking existence of file: {resolved_file_path} for task {task.task_id}")
            if os.path.exists(resolved_file_path):
                output_message = f"File '{resolved_file_path}' exists. Further debugging steps not implemented."
                findings_summary = f"File found: {resolved_file_path}. Ready for debugging."
                result_data_content["file_exists"] = True
                print(f"[{self.agent_id}] File '{resolved_file_path}' found.")
            else:
                # Still "completed" because the check was performed. The finding is the result.
                output_message = f"File not found: {resolved_file_path}. Cannot proceed with debugging."
                findings_summary = f"File not found: {resolved_file_path}."
                result_data_content["file_exists"] = False
                # Optionally, could set status to "failed" if file-not-found is a hard stop for any debugging.
                # For now, let's consider the check itself as the completed task.
                print(f"[{self.agent_id}] File '{resolved_file_path}' not found.")

            result_data_content["findings_summary"] = findings_summary

        result = ExecutionResult(
            task_id=task.task_id,
            status=status,
            output=output_message,
            data=result_data_content,
            error_message=output_message if status == "failed" else None # Only if overall task failed
        )

        if task.source_agent_id:
            result_channel = f"task_results_{task.source_agent_id}"
            await self._message_bus.publish(result_channel, result)
            print(f"[{self.agent_id}] Published debugging result for task {task.task_id} to {result_channel}.")
        else:
            print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id. Cannot publish result.")

    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                capability_id="debug_code_runtime",
                task_type="debugging_runtime_analysis",
                description="Analyzes code for runtime errors, helps set breakpoints, and inspects variables.",
                keywords=["debug", "file", "error", "runtime", "breakpoint", "inspect", "step", "through"], # Added "file", atomized "step through"
                required_input_keys=["file_path", "code_block_id_or_lines", "execution_parameters"], # Example keys
                generates_output_keys=["debug_session_id", "findings_summary", "suggested_fixes"] # Example keys
            )
        ]

    async def _task_listener_loop(self):
        channel_name = "debugging_tasks"
        self._task_queue = await self._message_bus.subscribe(channel_name)
        print(f"[{self.agent_id}] Subscribed to '{channel_name}'. Listening for tasks...")
        try:
            while True:
                message = await self._task_queue.get()
                if isinstance(message, Task):
                    if message.target_agent_id == self.agent_id or message.target_agent_id is None:
                        asyncio.create_task(self._process_task(message))
                elif message == f"stop_listening_{channel_name}":
                    print(f"[{self.agent_id}] Stop signal received for '{channel_name}' listener.")
                    break
                if self._task_queue: self._task_queue.task_done()
        except asyncio.CancelledError:
            print(f"[{self.agent_id}] Task listener for '{channel_name}' cancelled.")
        finally:
            if self._task_queue: await self._message_bus.unsubscribe(channel_name, self._task_queue)
            print(f"[{self.agent_id}] Unsubscribed and stopped listening on '{channel_name}'.")

    async def _discovery_listener_loop(self):
        channel_name = "system_discovery_channel"
        self._discovery_queue = await self._message_bus.subscribe(channel_name)
        print(f"[{self.agent_id}] Subscribed to '{channel_name}'. Listening for discovery requests...")
        try:
            while True:
                message = await self._discovery_queue.get()
                if isinstance(message, dict) and message.get("type") == "request_capabilities":
                    response_channel = message.get("response_channel")
                    if response_channel:
                        capabilities = await self.get_capabilities()
                        await self._message_bus.publish(response_channel, {
                            "type": "agent_capabilities_response",
                            "agent_id": self.agent_id,
                            "capabilities": capabilities
                        })
                elif message == f"stop_listening_{channel_name}":
                    print(f"[{self.agent_id}] Stop signal received for '{channel_name}' listener.")
                    break
                if self._discovery_queue: self._discovery_queue.task_done()
        except asyncio.CancelledError:
            print(f"[{self.agent_id}] Discovery listener for '{channel_name}' cancelled.")
        finally:
            if self._discovery_queue: await self._message_bus.unsubscribe(channel_name, self._discovery_queue)
            print(f"[{self.agent_id}] Unsubscribed and stopped listening on '{channel_name}'.")

    async def start_listening(self):
        self._listener_tasks.append(asyncio.create_task(self._task_listener_loop()))
        self._listener_tasks.append(asyncio.create_task(self._discovery_listener_loop()))
        print(f"[{self.agent_id}] All listeners started.")

    async def stop_listening(self):
        print(f"[{self.agent_id}] Requesting listeners to stop...")
        task_channel_name = "debugging_tasks"
        discovery_channel_name = "system_discovery_channel"
        await self._message_bus.publish(task_channel_name, f"stop_listening_{task_channel_name}")
        await self._message_bus.publish(discovery_channel_name, f"stop_listening_{discovery_channel_name}")
        if self._listener_tasks:
            await asyncio.gather(*self._listener_tasks, return_exceptions=True)
        print(f"[{self.agent_id}] All listeners stopped and tasks gathered.")

    # --- ACI Stubs ---
    async def send_message(self, target_agent_id: str, message_content: Any, message_type: str = "generic") -> bool:
        print(f"[{self.agent_id}] send_message to {target_agent_id} called (stub). Content: {message_content}")
        return True
    async def receive_message(self) -> Optional[Any]:
        print(f"[{self.agent_id}] receive_message called (stub).")
        return None
    async def post_task(self, task: Task) -> bool:
        print(f"[{self.agent_id}] post_task called (stub). Task: {task.task_id}")
        return False
    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[ExecutionResult]:
        print(f"[{self.agent_id}] get_task_result for {task_id} called (stub).")
        return None
    def register_event_listener(self, event_type: str, callback: Callable[[Any], None]) -> bool:
        print(f"[{self.agent_id}] register_event_listener for {event_type} called (stub).")
        return True
    async def emit_event(self, event_type: str, event_data: Any) -> bool:
        print(f"[{self.agent_id}] emit_event {event_type} called (stub). Data: {event_data}")
        return True
