# novapilot_agents/DocumentationAgent/doc_generator.py
import asyncio
import uuid # For _get_project_context if included
from typing import Optional, Any, Callable, Dict, List

from novapilot_core.aci import AgentCommunicationInterface
from novapilot_core.models import Task, ExecutionResult, AgentCapability, ProjectContext
from novapilot_core.message_bus import message_bus

class DocumentationAgent(AgentCommunicationInterface):
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
        # Using the same functional version as RefactoringAgent
        if self._project_context_cache:
            return self._project_context_cache
        request_id = str(uuid.uuid4())
        response_channel = f"agent_context_response_{self.agent_id}_{request_id}"
        context_response_queue = None
        try:
            context_response_queue = await self._message_bus.subscribe(response_channel)
            request_message = {"type": "get_project_context", "response_channel": response_channel}
            print(f"[{self.agent_id}] Requesting ProjectContext on 'context_requests'. Expecting response on '{response_channel}'.")
            await self._message_bus.publish("context_requests", request_message)
            project_context_response = await asyncio.wait_for(context_response_queue.get(), timeout=5.0)
            if isinstance(project_context_response, ProjectContext):
                self._project_context_cache = project_context_response
                print(f"[{self.agent_id}] Received and cached ProjectContext: ID={self._project_context_cache.project_id if self._project_context_cache else 'N/A'}")
                return self._project_context_cache
        except asyncio.TimeoutError:
            print(f"[{self.agent_id}] Timed out waiting for ProjectContext response on '{response_channel}'.")
        except Exception as e:
            print(f"[{self.agent_id}] Error during _get_project_context: {e}")
        finally:
            if context_response_queue:
                await self._message_bus.unsubscribe(response_channel, context_response_queue)
        return None

    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received Documentation task: {task.description}, Type: {task.task_type}, Data: {task.data}")

        # Inputs expected for "generate_function_docstring" capability:
        # required_input_keys=["file_path", "function_name", "code_block_lines"] (code_block_lines is placeholder for now)
        original_file_path = task.data.get("file_path")
        function_name = task.data.get("function_name")
        # code_block_lines = task.data.get("code_block_lines") # Not used in this basic impl, but expected

        status = "completed"
        output_message = ""
        result_data_content = {"original_request_description": task.description}
        resolved_file_path = original_file_path

        # Basic input validation for this specific task type simulation
        if not all([original_file_path, function_name]):
            status = "failed"
            missing = []
            if not original_file_path: missing.append("file_path")
            if not function_name: missing.append("function_name")
            # Not checking for code_block_lines yet in this basic version
            output_message = f"Missing required data for docstring generation: {', '.join(missing)}."
            result_data_content["error"] = output_message
            print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")
        else:
            project_ctx = await self._get_project_context()
            if project_ctx and project_ctx.root_path:
                if not os.path.isabs(original_file_path): # Requires import os
                    resolved_file_path = os.path.join(project_ctx.root_path, original_file_path)
                    print(f"[{self.agent_id}] Resolved relative path '{original_file_path}' to '{resolved_file_path}'.")
            elif not project_ctx:
                print(f"[{self.agent_id}] Warning: ProjectContext not available. Assuming '{original_file_path}' is absolute or accessible.")

            result_data_content["target_file_path"] = resolved_file_path
            result_data_content["function_name"] = function_name

            # Simulate docstring generation
            dummy_docstring = f'"""This is a generated docstring for {function_name} in file {resolved_file_path}."""'
            result_data_content["generated_docstring"] = dummy_docstring
            output_message = f"Simulated docstring generation for function '{function_name}' in file '{resolved_file_path}'."
            print(f"[{self.agent_id}] {output_message}")

        result = ExecutionResult(
            task_id=task.task_id,
            status=status,
            output=output_message,
            data=result_data_content,
            error_message=output_message if status == "failed" else None
        )

        if task.source_agent_id:
            result_channel = f"task_results_{task.source_agent_id}"
            await self._message_bus.publish(result_channel, result)
            print(f"[{self.agent_id}] Published documentation result for task {task.task_id} to {result_channel}.")
        else:
            print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id. Cannot publish result.")

    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                capability_id="generate_function_docstring",
                task_type="documentation_generate_docstring",
                description="Generates a docstring for a given function or method.",
                keywords=["documentation", "docstring", "generate docs", "function", "method", "comment"],
                required_input_keys=["file_path", "function_name", "code_block_lines"], # Example keys
                generates_output_keys=["generated_docstring", "target_file_path"] # Example keys
            ),
            AgentCapability(
                capability_id="generate_readme_section",
                task_type="documentation_generate_readme",
                description="Generates a section for a README.md file based on project details or specific features.",
                keywords=["documentation", "readme", "generate docs", "project description", "feature summary"],
                required_input_keys=["topic_description", "output_readme_path"], # Example keys
                generates_output_keys=["generated_readme_section", "target_readme_path"]
            )
        ]

    async def _task_listener_loop(self):
        channel_name = "documentation_tasks"
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
        task_channel_name = "documentation_tasks"
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
