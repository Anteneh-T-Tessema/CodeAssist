# novapilot_agents/EnvironmentManagementAgent/env_manager.py
import asyncio
import uuid
import os
from typing import Optional, Any, Callable, Dict, List

from novapilot_core.aci import AgentCommunicationInterface
from novapilot_core.models import Task, ExecutionResult, AgentCapability, ProjectContext
from novapilot_core.message_bus import message_bus

class EnvironmentManagementAgent(AgentCommunicationInterface):
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
        print(f"[{self.agent_id}] Received EnvMgmt task: {task.description}, Type: {task.task_type}, Data: {task.data}")

        action = task.data.get("action")
        package_name = task.data.get("package_name")
        venv_path_request = task.data.get("venv_path")

        status = "completed"
        output_message = ""
        result_data_content = {"original_request_description": task.description}

        if task.task_type == "env_list_python_dependencies": # Matches new capability's task_type
            # Simulate listing dependencies
            dummy_deps = ["requests==2.25.1 (simulated)", "numpy==1.20.3 (simulated)"]
            result_data_content["dependencies_listed"] = dummy_deps
            output_message = f"Simulated listing of {len(dummy_deps)} dependencies."
            print(f"[{self.agent_id}] {output_message}")

        elif task.task_type == "env_modify_python_dependency": # Matches new capability's task_type
            action = task.data.get("action") # Action is expected from this task type
            package_name = task.data.get("package_name") # Package name is expected

            if not action:
                status = "failed"
                output_message = "Missing 'action' in task data for modify_python_dependency."
            elif not package_name:
                status = "failed"
                output_message = f"Missing 'package_name' for action '{action}' in modify_python_dependency."
            elif action.lower() in ["install", "add", "update", "remove"]:
                output_message = f"Simulated '{action}' for package '{package_name}'. Version spec '{task.data.get('version_spec', 'any')}'."
                result_data_content["action_performed"] = action
                result_data_content["package_name"] = package_name
                result_data_content["version_spec_used"] = task.data.get('version_spec', 'any')
                result_data_content["dependency_management_log"] = f"Successfully simulated {action} for {package_name}."
                print(f"[{self.agent_id}] {output_message}")
            else:
                status = "failed"
                output_message = f"Unsupported action '{action}' for modify_python_dependency."

            if status == "failed":
                 result_data_content["error"] = output_message
                 print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")

        elif task.task_type == "env_setup_python_venv": # Existing logic for this
            if not venv_path_request:
                status = "failed"
                output_message = "Missing 'venv_path' in task data for virtual environment setup."
            else:
                project_ctx = await self._get_project_context()
                resolved_venv_path = venv_path_request
                if project_ctx and project_ctx.root_path and not os.path.isabs(venv_path_request):
                    resolved_venv_path = os.path.join(project_ctx.root_path, venv_path_request)
                    print(f"[{self.agent_id}] Resolved relative venv_path '{venv_path_request}' to '{resolved_venv_path}'.")

                output_message = f"Simulated setup of virtual environment at '{resolved_venv_path}'. Python version '{task.data.get('python_version', 'system default')}'."
                result_data_content["venv_path_created_simulated"] = resolved_venv_path
                result_data_content["python_version_used_simulated"] = task.data.get('python_version', 'system default')
                result_data_content["venv_activation_command"] = f"source {resolved_venv_path}/bin/activate (simulated)"
                print(f"[{self.agent_id}] {output_message}")

            if status == "failed":
                 result_data_content["error"] = output_message
                 print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")
        else:
            status = "failed"
            output_message = f"Unknown or unhandled task type '{task.task_type}' for EnvironmentManagementAgent."
            result_data_content["error"] = output_message
            print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")

    # ... (rest of the result publishing logic remains the same) ...
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
            print(f"[{self.agent_id}] Published environment management result for task {task.task_id} to {result_channel}.")
        else:
            print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id. Cannot publish result.")

    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                capability_id="list_python_dependencies", # New specific capability ID
                task_type="env_list_python_dependencies", # New specific task type
                description="Lists Python project dependencies.",
                keywords=["list", "show", "view", "python", "dependencies", "package", "packages", "installed"], # Atomized
                required_input_keys=[], # No specific package_name needed for list
                generates_output_keys=["dependencies_listed", "status_message"]
            ),
            AgentCapability(
                capability_id="modify_python_dependency", # More general name for add/remove/update
                task_type="env_modify_python_dependency", # New specific task type
                description="Manages Python project dependencies (e.g., install, add, update, remove).",
                keywords=["environment", "dependencies", "python", "pip", "poetry", "install", "update", "remove", "add", "package"], # Added "add"
                required_input_keys=["action", "package_name"], # version_spec can be optional in task.data
                generates_output_keys=["dependencies_updated_list", "dependency_management_log", "status_message"]
            ),
            AgentCapability( # Existing capability for venv setup
                capability_id="setup_virtual_environment",
                task_type="env_setup_python_venv",
                description="Sets up or activates a Python virtual environment.",
                keywords=["environment", "virtualenv", "venv", "python", "setup", "activate", "create"], # Added "create"
                required_input_keys=["venv_path", "python_version"],
                generates_output_keys=["venv_activation_command", "status_message"]
            )
        ]

    async def _task_listener_loop(self):
        channel_name = "environment_management_tasks"
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
        task_channel_name = "environment_management_tasks"
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
