# novapilot_agents/RefactoringAgent/refactorer.py
import asyncio
import uuid # Added for _get_project_context
from typing import Optional, Any, Callable, Dict, List

from novapilot_core.aci import AgentCommunicationInterface
from novapilot_core.models import Task, ExecutionResult, AgentCapability, ProjectContext
from novapilot_core.message_bus import message_bus

class RefactoringAgent(AgentCommunicationInterface):
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

        request_id = str(uuid.uuid4()) # Requires import uuid
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
                    # print(f"[{self.agent_id}] Unsubscribed from temporary context response channel '{response_channel}'.") # Optional: reduce noise

        except Exception as e:
            print(f"[{self.agent_id}] Error during _get_project_context: {e}")
            if context_response_queue and response_channel:
                 try:
                     await self._message_bus.unsubscribe(response_channel, context_response_queue)
                     # print(f"[{self.agent_id}] Unsubscribed from temporary context response channel '{response_channel}' due to exception.") # Optional: reduce noise
                 except Exception as unsub_e:
                     print(f"[{self.agent_id}] Error unsubscribing from '{response_channel}': {unsub_e}")
            return None


    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received task: {task.description}, Type: {task.task_type}, Data: {task.data}")
        await asyncio.sleep(0.1)

        output_message = f"Refactoring for '{task.description}' not implemented yet."
        result_data_content = {"status_message": "not_implemented", "refactoring_summary": "No changes applied."}

        result = ExecutionResult(
            task_id=task.task_id,
            status="not_implemented",
            output=output_message,
            data=result_data_content
        )
        if task.source_agent_id:
            result_channel = f"task_results_{task.source_agent_id}"
            await self._message_bus.publish(result_channel, result)
        else:
            print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id. Cannot publish result.")

    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                capability_id="refactor_rename_variable",
                task_type="refactoring_rename_variable",
                description="Renames a variable across relevant scopes within a file or project.",
                keywords=["refactor", "rename", "variable", "identifier", "code modification"],
                required_input_keys=["file_path", "old_name", "new_name", "line_number_or_scope"], # Example keys
                generates_output_keys=["modified_files_list", "summary_of_changes"] # Example keys
            ),
            AgentCapability(
                capability_id="refactor_extract_method",
                task_type="refactoring_extract_method",
                description="Extracts a block of code into a new method.",
                keywords=["refactor", "extract", "method", "function", "code modification"],
                required_input_keys=["file_path", "code_block_to_extract_lines", "new_method_name"], # Example keys
                generates_output_keys=["modified_files_list", "new_method_signature", "summary_of_changes"]
            )
        ]

    async def _task_listener_loop(self):
        channel_name = "refactoring_tasks"
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
        self._listener_tasks.clear()
        self._listener_tasks.append(asyncio.create_task(self._task_listener_loop()))
        self._listener_tasks.append(asyncio.create_task(self._discovery_listener_loop()))
        print(f"[{self.agent_id}] All listeners started.")

    async def stop_listening(self):
        print(f"[{self.agent_id}] Requesting listeners to stop...")
        task_channel_name = "refactoring_tasks"
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
