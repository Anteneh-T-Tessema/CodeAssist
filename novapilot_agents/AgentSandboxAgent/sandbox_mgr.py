# novapilot_agents/AgentSandboxAgent/sandbox_mgr.py
import asyncio
import uuid
import os
from typing import Optional, Any, Callable, Dict, List

from novapilot_core.aci import AgentCommunicationInterface
from novapilot_core.models import Task, ExecutionResult, AgentCapability, ProjectContext
from novapilot_core.message_bus import message_bus

class AgentSandboxAgent(AgentCommunicationInterface):
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

    # In AgentSandboxAgent class:
    # Ensure 'os', 'uuid', 'ProjectContext', 'Task', 'ExecutionResult', 'AgentCapability',
    # 'List', 'Optional', 'Dict', 'Any', 'asyncio' are available.

    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received AgentSandbox task: {task.description}, Type: {task.task_type}, Data: {task.data}")

        status = "completed"
        output_message = ""
        result_data_content = {"original_request_description": task.description}
        sandbox_id_for_op = task.data.get("sandbox_id_or_config", str(uuid.uuid4())[:8]) # Use provided or generate dummy

        # project_ctx = await self._get_project_context() # Available if needed

        if task.task_type == "sandbox_execute":
            code_to_execute = task.data.get("code_to_execute")
            language = task.data.get("language")
            # sandbox_parameters = task.data.get("sandbox_parameters") # Not used in this simulation

            if not all([code_to_execute, language]):
                status = "failed"
                missing = []
                if not code_to_execute: missing.append("code_to_execute")
                if not language: missing.append("language")
                output_message = f"Missing required data for sandbox_execute: {', '.join(missing)}."
                result_data_content["error"] = output_message
                print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")
            else:
                await asyncio.sleep(0.2) # Simulate execution time
                sim_stdout = ""
                sim_stderr = ""
                sim_exit_code = 0

                if str(language).lower() == "python":
                    if "print(" in str(code_to_execute):
                        # Try to extract what's inside print() for a slightly more dynamic simulation
                        try:
                            # Very naive extraction, assumes print("...") or print('...')
                            printed_content = str(code_to_execute).split("print(", 1)[1].split(")",1)[0]
                            # Remove quotes if present
                            if printed_content.startswith("'") and printed_content.endswith("'"):
                                printed_content = printed_content[1:-1]
                            elif printed_content.startswith('"') and printed_content.endswith('"'):
                                printed_content = printed_content[1:-1]
                            sim_stdout = f"Simulated Python output: {printed_content}"
                        except:
                            sim_stdout = "Simulated Python output: Execution produced some text."
                    elif "error" in str(code_to_execute).lower():
                        sim_stderr = "Simulated Python error: Something went wrong!"
                        sim_exit_code = 1
                    else:
                        sim_stdout = "Simulated Python code executed successfully without specific print."
                else:
                    sim_stdout = f"Simulated execution of {language} code."

                output_message = f"Simulated execution of '{language}' code in sandbox '{sandbox_id_for_op}'. Exit code: {sim_exit_code}."
                result_data_content["sandbox_id"] = sandbox_id_for_op
                result_data_content["execution_stdout"] = sim_stdout
                result_data_content["execution_stderr"] = sim_stderr
                result_data_content["exit_code"] = sim_exit_code
                # result_data_content["resource_usage"] = {"cpu": "0.1s", "memory": "10MB"} # Example
                print(f"[{self.agent_id}] {output_message}")

        elif task.task_type == "sandbox_manage_env":
            sandbox_action = task.data.get("sandbox_action")
            # sandbox_id_or_config = task.data.get("sandbox_id_or_config") # Already got as sandbox_id_for_op

            if not sandbox_action:
                status = "failed"
                output_message = "Missing 'sandbox_action' in task data for sandbox_manage_env."
                result_data_content["error"] = output_message
                print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")
            else:
                await asyncio.sleep(0.1) # Simulate action time
                action_lower = str(sandbox_action).lower()
                if action_lower in ["create", "delete", "get_status"]:
                    output_message = f"Simulated '{action_lower}' action for sandbox '{sandbox_id_for_op}'."
                    result_data_content["sandbox_id"] = sandbox_id_for_op
                    result_data_content["sandbox_status"] = f"simulated_{action_lower}_completed" if action_lower != "get_status" else "simulated_ready"
                    result_data_content["action_log"] = f"Action '{action_lower}' on sandbox '{sandbox_id_for_op}' simulated."
                else:
                    status = "failed"
                    output_message = f"Unsupported sandbox_action: '{sandbox_action}'."
                    result_data_content["error"] = output_message
                print(f"[{self.agent_id}] {output_message}")

        else:
            status = "failed"
            output_message = f"Unknown or unsupported task type '{task.task_type}' for AgentSandboxAgent."
            result_data_content["error"] = output_message
            print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")

        if status == "failed" and "error" not in result_data_content :
            result_data_content["error"] = output_message

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
            print(f"[{self.agent_id}] Published AgentSandbox result for task {task.task_id} to {result_channel}.")
        else:
            print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id. Cannot publish result.")

    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                capability_id="sandbox_execute_code",
                task_type="sandbox_execute",
                description="Executes a given code block or script within a secure, isolated sandbox environment.",
                keywords=["sandbox", "execute", "run", "codeblock", "script", "isolated", "secure", "sandboxed"],
                required_input_keys=["code_to_execute", "language", "sandbox_parameters"], # sandbox_parameters: e.g., allowed network, file access
                generates_output_keys=["sandbox_id", "execution_stdout", "execution_stderr", "exit_code", "resource_usage"]
            ),
            AgentCapability(
                capability_id="sandbox_manage_environment",
                task_type="sandbox_manage_env",
                description="Manages sandbox environments, such as creating, deleting, or configuring them.",
                keywords=["sandbox", "environment", "manage", "create", "delete", "configure"],
                required_input_keys=["sandbox_action", "sandbox_id_or_config"], # sandbox_action: "create", "delete", "get_status"
                generates_output_keys=["sandbox_status", "action_log"]
            )
        ]

    async def _task_listener_loop(self):
        channel_name = "agent_sandbox_tasks"
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
        task_channel_name = "agent_sandbox_tasks"
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
