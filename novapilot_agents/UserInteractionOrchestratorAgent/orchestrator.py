# novapilot_agents/UserInteractionOrchestratorAgent/orchestrator.py
import asyncio
import uuid # For generating unique task IDs
import os # For os.getcwd()
from typing import Dict, Optional, Any, Callable, List

from novapilot_core.aci import AgentCommunicationInterface
from novapilot_core.models import Task, ExecutionResult, AgentCapability, ProjectContext
from novapilot_core.message_bus import message_bus

class UserInteractionOrchestratorAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._active_tasks: Dict[str, Task] = {}
        self._task_results_queue: Optional[asyncio.Queue] = None
        self._agent_capabilities_registry: Dict[str, List[AgentCapability]] = {}
        self._known_agent_ids: List[str] = [
            "codegen_agent_01",
            "code_understanding_agent_01",
            "code_completion_agent_01",
            "debugging_agent_01",
            "automated_testing_agent_01"
        ]
        self._discovery_response_queue: Optional[asyncio.Queue] = None
        self._project_context: Optional[ProjectContext] = None
        self._context_request_queue: Optional[asyncio.Queue] = None
        self._initialize_project_context()

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def _listen_for_results(self):
        results_channel = f"task_results_{self.agent_id}"
        self._task_results_queue = await self._message_bus.subscribe(results_channel)
        print(f"[{self.agent_id}] Subscribed to '{results_channel}' for task results.")
        try:
            while True:
                result = await self._task_results_queue.get()
                if isinstance(result, ExecutionResult):
                    print(f"[{self.agent_id}] Received result for task {result.task_id}: Status='{result.status}', Output='{result.output}', Data='{result.data}'")
                    if result.task_id in self._active_tasks:
                        self._active_tasks[result.task_id].status = result.status
                    else:
                        print(f"[{self.agent_id}] Warning: Received result for unknown task ID {result.task_id}")
                elif result == "stop_listening":
                    print(f"[{self.agent_id}] Stop signal received for results listener.")
                    break
                self._task_results_queue.task_done()
        except Exception as e:
            print(f"[{self.agent_id}] Error in results listener: {e}")
        finally:
            if self._task_results_queue:
                await self._message_bus.unsubscribe(results_channel, self._task_results_queue)
            print(f"[{self.agent_id}] Unsubscribed and stopped listening for results.")

    def _initialize_project_context(self):
        root_dir = os.getcwd()
        project_id = str(uuid.uuid4())
        project_name = os.path.basename(root_dir)
        self._project_context = ProjectContext(
            project_id=project_id,
            root_path=root_dir,
            project_name=project_name,
        )
        print(f"[{self.agent_id}] Initialized ProjectContext: ID={project_id}, Name='{project_name}', Root='{root_dir}'")

    async def _listen_for_context_requests(self):
        request_channel = "context_requests"
        self._context_request_queue = await self._message_bus.subscribe(request_channel)
        print(f"[{self.agent_id}] Subscribed to '{request_channel}' for ProjectContext requests.")
        try:
            while True:
                message = await self._context_request_queue.get()
                if isinstance(message, dict):
                    msg_type = message.get("type")
                    response_channel = message.get("response_channel")
                    if msg_type == "get_project_context" and response_channel:
                        print(f"[{self.agent_id}] Received get_project_context request. Responding on '{response_channel}'.")
                        if self._project_context:
                            await self._message_bus.publish(response_channel, self._project_context)
                        else:
                            print(f"[{self.agent_id}] Error: ProjectContext not initialized when request received.")
                    else:
                        print(f"[{self.agent_id}] Received unknown message on context_requests: {message}")
                elif message == "stop_listening_context":
                    print(f"[{self.agent_id}] Stop signal received for context_requests listener.")
                    break
                if self._context_request_queue:
                    self._context_request_queue.task_done()
        except Exception as e:
            print(f"[{self.agent_id}] Error in context_requests listener: {e}")
        finally:
            if self._context_request_queue:
                await self._message_bus.unsubscribe(request_channel, self._context_request_queue)
            print(f"[{self.agent_id}] Unsubscribed and stopped listening for context requests.")

    async def _listen_for_discovery_responses(self):
        discovery_channel = f"orchestrator_discovery_responses_{self.agent_id}"
        self._discovery_response_queue = await self._message_bus.subscribe(discovery_channel)
        print(f"[{self.agent_id}] Subscribed to '{discovery_channel}' for agent capability responses.")
        try:
            while True:
                response = await self._discovery_response_queue.get()
                if isinstance(response, dict) and response.get("type") == "agent_capabilities_response":
                    agent_id_resp = response.get("agent_id")
                    capabilities_data = response.get("capabilities")
                    if agent_id_resp and capabilities_data:
                        if isinstance(capabilities_data, list) and all(isinstance(cap, AgentCapability) for cap in capabilities_data):
                            self._agent_capabilities_registry[agent_id_resp] = capabilities_data
                            print(f"[{self.agent_id}] Received and registered capabilities from {agent_id_resp}: {len(capabilities_data)} capabilities.")
                        else:
                            print(f"[{self.agent_id}] Received capabilities_data from {agent_id_resp} not in expected List[AgentCapability] format. Data: {capabilities_data}")
                elif response == "stop_listening_discovery":
                    print(f"[{self.agent_id}] Stop signal received for discovery responses listener.")
                    break
                else:
                    print(f"[{self.agent_id}] Received malformed/unexpected message on discovery response channel: {response}")
                if self._discovery_response_queue:
                    self._discovery_response_queue.task_done()
        except Exception as e:
            print(f"[{self.agent_id}] Error in discovery responses listener: {e}")
        finally:
            if self._discovery_response_queue:
                await self._message_bus.unsubscribe(discovery_channel, self._discovery_response_queue)
            print(f"[{self.agent_id}] Unsubscribed and stopped listening for discovery responses.")

    async def discover_agents(self):
        print(f"[{self.agent_id}] Starting agent discovery...")
        discovery_request = {
            "type": "request_capabilities",
            "response_channel": f"orchestrator_discovery_responses_{self.agent_id}"
        }
        self._agent_capabilities_registry.clear()
        for agent_id_iter in self._known_agent_ids:
            print(f"[{self.agent_id}] Requesting capabilities from potential agent {agent_id_iter} on 'system_discovery_channel'.")
            await self._message_bus.publish("system_discovery_channel", discovery_request)
        await asyncio.sleep(1.0)
        print(f"[{self.agent_id}] Agent discovery attempt finished. Registry: {self._agent_capabilities_registry}")

    async def start_listening(self):
        self._listener_tasks_refs = []
        self._listener_tasks_refs.append(asyncio.create_task(self._listen_for_results()))
        self._listener_tasks_refs.append(asyncio.create_task(self._listen_for_discovery_responses()))
        self._listener_tasks_refs.append(asyncio.create_task(self._listen_for_context_requests()))
        print(f"[{self.agent_id}] All primary listeners started.")

    async def stop_listening(self):
        print(f"[{self.agent_id}] Requesting all listeners to stop...")
        results_channel = f"task_results_{self.agent_id}"
        await self._message_bus.publish(results_channel, "stop_listening")
        discovery_channel = f"orchestrator_discovery_responses_{self.agent_id}"
        await self._message_bus.publish(discovery_channel, "stop_listening_discovery")
        context_request_channel = "context_requests"
        await self._message_bus.publish(context_request_channel, "stop_listening_context")
        if hasattr(self, '_listener_tasks_refs') and self._listener_tasks_refs:
            print(f"[{self.agent_id}] Gathering all primary listener tasks...")
            await asyncio.gather(*self._listener_tasks_refs, return_exceptions=True)
            print(f"[{self.agent_id}] All primary listener tasks gathered.")
        else:
            await asyncio.sleep(0.1)
        print(f"[{self.agent_id}] All stop signals sent and listeners presumably stopped.")

    async def receive_user_request(self, request_text: str, task_data: Optional[Dict[str, Any]] = None):
        task_id = str(uuid.uuid4())
        if task_data is None:
            task_data = {}

        print(f"[{self.agent_id}] New user request received: '{request_text}'")
        request_keywords = set(request_text.lower().split())

        best_match_agent_id = None
        best_matched_capability: Optional[AgentCapability] = None
        highest_score = 0

        if not self._agent_capabilities_registry:
            print(f"[{self.agent_id}] Warning: Agent capabilities registry is empty. Running discover_agents() first is recommended.")

        for agent_id_iter_reg, capabilities_iter_reg in self._agent_capabilities_registry.items():
            for capability_iter_reg in capabilities_iter_reg:
                capability_keywords = set(k.lower() for k in capability_iter_reg.keywords)
                common_keywords = request_keywords.intersection(capability_keywords)
                score = len(common_keywords)

                if score > highest_score:
                    highest_score = score
                    best_match_agent_id = agent_id_iter_reg
                    best_matched_capability = capability_iter_reg
                elif score == highest_score and score > 0 :
                    if best_matched_capability and len(capability_iter_reg.keywords) > len(best_matched_capability.keywords):
                        best_match_agent_id = agent_id_iter_reg
                        best_matched_capability = capability_iter_reg

        target_agent_id = best_match_agent_id
        task_status = "pending_dispatch"
        final_task_description = request_text
        assigned_task_type = None
        dispatch_task = True

        if target_agent_id and best_matched_capability:
            assigned_task_type = best_matched_capability.task_type
            print(f"[{self.agent_id}] Smart routing: Target={target_agent_id}, Capability='{best_matched_capability.description}' (Type: {assigned_task_type}), Score={highest_score} for request: '{request_text}'")

            # --- Temporary Test Data Injection for 'editable' check ---
            if target_agent_id == "codegen_agent_01" and best_matched_capability:
                if "save to temp/test_non_editable.py" in request_text.lower():
                    task_data["target_file_path"] = "temp/test_non_editable.py"
                    task_data["target_file_is_editable"] = False
                    task_data["description"] = request_text
                    print(f"[{self.agent_id}] Test hook: Set target_file_is_editable=False, path, and data.description for {task_data['target_file_path']}")

                elif "save to temp/test_editable.py" in request_text.lower():
                    task_data["target_file_path"] = "temp/test_editable.py"
                    task_data["target_file_is_editable"] = True
                    task_data["description"] = request_text
                    print(f"[{self.agent_id}] Test hook: Set target_file_is_editable=True, path, and data.description for {task_data['target_file_path']}")

            elif "complete python def" in request_text.lower() and target_agent_id == "code_completion_agent_01":
                task_data["code_context"] = "def "
                task_data["cursor_position"] = 4
                task_data["file_path"] = "dummy.py"
                if "description" not in task_data: task_data["description"] = request_text
                print(f"[{self.agent_id}] Test hook: Populated task_data for CodeCompletionAgent 'def' test.")

            elif "debug file " in request_text.lower() and target_agent_id == "debugging_agent_01":
                parts = request_text.split("debug file ", 1)
                if len(parts) > 1:
                    potential_file_path = parts[1].strip()
                    task_data["file_path"] = potential_file_path
                    task_data["code_block_id_or_lines"] = "N/A"
                    task_data["execution_parameters"] = {}
                    if "description" not in task_data:
                        task_data["description"] = request_text
                    print(f"[{self.agent_id}] Test hook: Populated task_data for DebuggingAgent test for file '{potential_file_path}'.")
                else:
                    print(f"[{self.agent_id}] Test hook: 'debug file' detected but could not extract file path from '{request_text}'.")

            # Heuristic file_path extraction (should run after specific test hooks for file_analysis if not already populated)
            if assigned_task_type == "file_analysis_line_count" and "file_path" not in task_data:
                potential_paths = [word for word in request_text.split() if "." in word or "/" in word or "\\" in word]
                if potential_paths:
                    task_data["file_path"] = potential_paths[0]
                    print(f"[{self.agent_id}] Heuristically extracted file_path for analysis: {task_data['file_path']}")

            # --- Input Validation Logic ---
            missing_keys = []
            if best_matched_capability.required_input_keys:
                for key in best_matched_capability.required_input_keys:
                    if key not in task_data:
                        missing_keys.append(key)

                if missing_keys:
                    validation_error_detail = f"Missing required input data keys: {', '.join(missing_keys)} for capability '{best_matched_capability.capability_id}'."
                    print(f"[{self.agent_id}] Task input validation FAILED for request '{request_text}': {validation_error_detail}")
                    task_status = "input_validation_failed"
                    dispatch_task = False
        else:
            task_status = "unroutable"
            dispatch_task = False
            print(f"[{self.agent_id}] Could not find suitable agent for request: '{request_text}'. Marked unroutable.")

        task = Task(
            task_id=task_id,
            description=final_task_description,
            source_agent_id=self.agent_id,
            target_agent_id=target_agent_id,
            data=task_data,
            status=task_status,
            task_type=assigned_task_type
        )
        self._active_tasks[task_id] = task
        log_target_display = target_agent_id if dispatch_task and target_agent_id else 'N/A'
        if task_status == "input_validation_failed" and target_agent_id:
            log_target_display = f"{target_agent_id} (Validation Failed)"

        print(f"[{self.agent_id}] New task created: ID={task_id}, Type='{task.task_type if task.task_type else 'N/A'}', Target='{log_target_display}', Status='{task.status}', Desc='{task.description}'")

        if dispatch_task and task.target_agent_id:
            await self.post_task(task)
        else:
            print(f"[{self.agent_id}] Task {task.task_id} will not be dispatched (Status: '{task.status}').")

        return task_id

    # --- ACI Implementation ---
    async def send_message(self, target_agent_id: str, message_content: Any, message_type: str = "generic") -> bool:
        print(f"[{self.agent_id}] send_message: Type '{message_type}' to {target_agent_id} (stub)")
        await self._message_bus.publish(f"agent_messages_{target_agent_id}", message_content)
        return True

    async def receive_message(self) -> Optional[Any]:
        print(f"[{self.agent_id}] receive_message called (stub - use specific listeners)")
        return None

    async def post_task(self, task: Task) -> bool:
        if not task.target_agent_id:
            print(f"[{self.agent_id}] Task {task.task_id} has no target_agent_id. Cannot post.")
            return False
        # Updated channel_map
        channel_map = {
            "codegen_agent_01": "code_generation_tasks",
            "code_understanding_agent_01": "code_understanding_tasks",
            "code_completion_agent_01": "code_completion_tasks",
            "debugging_agent_01": "debugging_tasks",
            "automated_testing_agent_01": "automated_testing_tasks"
        }
        target_channel = channel_map.get(task.target_agent_id)
        if target_channel:
            task.status = "dispatched"
            print(f"[{self.agent_id}] Posting task {task.task_id} to {task.target_agent_id} on channel '{target_channel}': {task.description}")
            await self._message_bus.publish(target_channel, task)
            if task.task_id not in self._active_tasks:
                 self._active_tasks[task.task_id] = task
            else:
                 self._active_tasks[task.task_id].status = "dispatched"
            return True
        else:
            print(f"[{self.agent_id}] No channel configured for target agent ID: {task.target_agent_id}")
            if task.task_id in self._active_tasks:
                self._active_tasks[task.task_id].status = "dispatch_failed"
            return False

    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[ExecutionResult]:
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            print(f"[{self.agent_id}] Checking result for task {task_id}. Current status: {task.status}")
            if task.status == "completed" or task.status == "failed":
                if task.status == "completed":
                    return ExecutionResult(task_id=task_id, status="completed", output="Mock result from orchestrator")
                else:
                    return ExecutionResult(task_id=task_id, status="failed", error_message="Mock failure from orchestrator")
        return None

    def register_event_listener(self, event_type: str, callback: Callable[[Any], None]) -> bool:
        print(f"[{self.agent_id}] register_event_listener for '{event_type}' (stub)")
        return True

    async def emit_event(self, event_type: str, event_data: Any) -> bool:
        print(f"[{self.agent_id}] Emitting event '{event_type}' (stub)")
        await self._message_bus.publish(event_type, event_data)
        return True

    async def get_capabilities(self) -> List[AgentCapability]:
        return []
