# novapilot_agents/AutomatedTestingAgent/test_automator.py
import asyncio
from typing import Optional, Any, Callable, Dict, List

from novapilot_core.aci import AgentCommunicationInterface
from novapilot_core.models import Task, ExecutionResult, AgentCapability, ProjectContext # Assuming ProjectContext might be useful
from novapilot_core.message_bus import message_bus

class AutomatedTestingAgent(AgentCommunicationInterface):
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
        print(f"[{self.agent_id}] _get_project_context called (placeholder - not fetching).")
        return None

    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received AutomatedTesting task: {task.description}, Type: {task.task_type}, Data: {task.data}")

        file_path_or_module = task.data.get("file_path_or_module")
        status = "completed" # Default, as the act of checking/simulating is the task.
        output_message = ""
        result_data_content = {
            "test_run_id": f"test_run_{task.task_id}", # Example session ID
            "input_file_path_or_module": file_path_or_module
        }

        if not file_path_or_module:
            status = "failed"
            output_message = "Missing 'file_path_or_module' in task data for testing."
            result_data_content["error"] = output_message
            print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")
        elif isinstance(file_path_or_module, str) and file_path_or_module.endswith("_test.py"):
            # This is a recognized test file (by simple convention)
            output_message = f"Simulated test run for '{file_path_or_module}': All tests passed."
            result_data_content["pass_count"] = 5 # Simulated
            result_data_content["fail_count"] = 0 # Simulated
            result_data_content["test_report_summary"] = "All tests passed (simulated)."
            result_data_content["recognized_as_test_file"] = True
            print(f"[{self.agent_id}] File '{file_path_or_module}' recognized as test file. Simulated success.")
        elif isinstance(file_path_or_module, str):
            # Provided path/module doesn't match the test file convention
            output_message = f"File or module '{file_path_or_module}' does not appear to be a recognized test file (e.g., ending in _test.py). No tests run."
            result_data_content["recognized_as_test_file"] = False
            result_data_content["status_message"] = "Not a recognized test file for this basic check."
            print(f"[{self.agent_id}] File '{file_path_or_module}' not recognized as a test file by current convention.")
        else: # file_path_or_module is not a string or is None (already handled by initial check but good for robustness)
            status = "failed"
            output_message = f"Invalid 'file_path_or_module' provided: {file_path_or_module}."
            result_data_content["error"] = output_message
            print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")


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
            print(f"[{self.agent_id}] Published automated testing result for task {task.task_id} to {result_channel}.")
        else:
            print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id. Cannot publish result.")

    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                capability_id="run_unit_tests",
                task_type="testing_run_unit_tests",
                description="Runs unit tests for a specified module or file.",
                keywords=["test", "tests", "unit", "run", "execute", "pytest", "unittest", "module", "file"],
                required_input_keys=["file_path_or_module", "test_suite_name"], # Example keys
                generates_output_keys=["test_run_id", "pass_count", "fail_count", "test_report_summary"] # Example keys
            ),
            AgentCapability(
                capability_id="generate_test_scaffolding",
                task_type="testing_generate_scaffolding",
                description="Generates boilerplate/scaffolding for new test files.",
                keywords=["generate", "scaffold", "new", "test", "file", "boilerplate", "tests"],
                required_input_keys=["file_path_to_test", "test_framework_preference"], # Example keys
                generates_output_keys=["generated_test_file_path", "scaffolding_details"] # Example keys
            )
        ]

    async def _task_listener_loop(self):
        channel_name = "automated_testing_tasks"
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
        task_channel_name = "automated_testing_tasks"
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
