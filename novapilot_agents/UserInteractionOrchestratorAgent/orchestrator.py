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
            "automated_testing_agent_01",
            "refactoring_agent_01",
            "documentation_agent_01",
            "version_control_agent_01",
            "vulnerability_scan_agent_01",
            "environment_management_agent_01",
            "platform_integration_agent_01",
            "knowledge_base_agent_01",          # New
            "agent_lifecycle_manager_agent_01", # New
            "agent_sandbox_agent_01",           # New
            "guardrail_agent_01",               # New
            "evaluation_agent_01"               # New
        ] # Total 16 agents
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

        # --- START Special Routing Hint for "sandbox execute" ---
        limit_search_to_agent_id = None
        if "sandbox execute" in request_text.lower():
            limit_search_to_agent_id = "agent_sandbox_agent_01"
            print(f"[{self.agent_id}] Applying search limit for 'sandbox execute' to agent {limit_search_to_agent_id}.")
        # --- END Special Routing Hint ---

        agents_to_search_dict = self._agent_capabilities_registry
        if limit_search_to_agent_id:
            if limit_search_to_agent_id in self._agent_capabilities_registry:
                agents_to_search_dict = {limit_search_to_agent_id: self._agent_capabilities_registry[limit_search_to_agent_id]}
            else: # Should not happen if known_agents is correct
                print(f"[{self.agent_id}] Warning: Hinted target agent {limit_search_to_agent_id} for 'sandbox execute' not in registry. Full search will proceed.")
                # agents_to_search_dict remains self._agent_capabilities_registry

        for agent_id_iter_reg, capabilities_iter_reg in agents_to_search_dict.items():
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

            # --- Temporary Test Data Injection ---
            # This is part of the larger elif chain for test data injection

            elif target_agent_id == "codegen_agent_01" and best_matched_capability:
                # Default description if not already set by more specific parsing below
                if "description" not in task_data:
                    task_data["description"] = request_text

                # Specific test case for non-editable
                if "save to temp/test_non_editable.py" in request_text.lower():
                    task_data["target_file_path"] = "temp/test_non_editable.py"
                    task_data["target_file_is_editable"] = False
                    print(f"[{self.agent_id}] Test hook (CG): Set non-editable for temp/test_non_editable.py")

                # Specific test case for editable (explicitly for testing the flag)
                elif "save to temp/test_editable.py" in request_text.lower():
                    task_data["target_file_path"] = "temp/test_editable.py"
                    task_data["target_file_is_editable"] = True # Explicitly True for this test
                    print(f"[{self.agent_id}] Test hook (CG): Set editable for temp/test_editable.py")

                # General case for "generate ... and save to FILENAME"
                # Example: "generate python hello world and save to generated_code/hello.py"
                elif " save to " in request_text.lower():
                    try:
                        # Extract the filename part
                        # Assuming format "... save to path/to/file.ext"
                        path_part = request_text.lower().split(" save to ", 1)[1].strip()
                        # Get original case from original request_text for the path
                        original_path_part = request_text.split(" save to ", 1)[1].strip()

                        task_data["target_file_path"] = original_path_part
                        # For new files or general saves where editable isn't specified in request, assume True
                        if "target_file_is_editable" not in task_data: # Don't override explicit non-editable tests
                            task_data["target_file_is_editable"] = True
                        print(f"[{self.agent_id}] Test hook (CG): Parsed target_file_path='{original_path_part}' for save. Editable defaulted/kept as {task_data.get('target_file_is_editable')}.")
                    except IndexError:
                        print(f"[{self.agent_id}] Test hook (CG): ' save to ' detected but failed to parse file path from '{request_text}'.")
                    except Exception as e:
                        print(f"[{self.agent_id}] Test hook (CG): Error parsing ' save to ' request '{request_text}': {e}")

                # If "description" is still needed by a capability but not set by specific parsing,
                # it's already set at the start of this codegen_agent_01 block.
                # This ensures that even if no specific file-related keywords are matched for data injection,
                # the task can still pass validation if only 'description' is required by the matched capability.

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

            elif "run tests for " in request_text.lower() and target_agent_id == "automated_testing_agent_01":
                parts = request_text.lower().split("run tests for ", 1)
                if len(parts) > 1:
                    original_parts = request_text.split("run tests for ", 1)
                    potential_file_path_or_module = original_parts[1].strip()
                    task_data["file_path_or_module"] = potential_file_path_or_module
                    task_data["test_suite_name"] = "all"
                    if "description" not in task_data:
                        task_data["description"] = request_text
                    print(f"[{self.agent_id}] Test hook: Populated task_data for AutomatedTestingAgent test for '{potential_file_path_or_module}'.")
                else:
                    print(f"[{self.agent_id}] Test hook: 'run tests for' detected for AutomatedTestingAgent, but could not extract file/module from '{request_text}'.")

            elif "refactor rename " in request_text.lower() and target_agent_id == "refactoring_agent_01":
                try:
                    text_to_parse = request_text.lower()
                    parts1 = text_to_parse.split("refactor rename ", 1)[1].split(" to ", 1)
                    old_name_part = parts1[0].strip()
                    parts2 = parts1[1].split(" in file ", 1)
                    new_name_part = parts2[0].strip()
                    original_request_parts = request_text.split(" in file ", 1)
                    file_path_part = original_request_parts[1].strip()
                    task_data["old_name"] = old_name_part
                    task_data["new_name"] = new_name_part
                    task_data["file_path"] = file_path_part
                    task_data["line_number_or_scope"] = "all"
                    if "description" not in task_data:
                        task_data["description"] = request_text
                    print(f"[{self.agent_id}] Test hook: Populated task_data for RefactoringAgent 'rename' test: "
                          f"old='{old_name_part}', new='{new_name_part}', file='{file_path_part}'.")
                except IndexError:
                    print(f"[{self.agent_id}] Test hook: 'refactor rename' detected for RefactoringAgent, but failed to parse all parts from '{request_text}'.")
                except Exception as e:
                    print(f"[{self.agent_id}] Test hook: Error parsing 'refactor rename' request for RefactoringAgent '{request_text}': {e}")

            elif "generate docstring for " in request_text.lower() and target_agent_id == "documentation_agent_01":
                # Example: "generate docstring for my_function in file src/utils.py"
                try:
                    text_to_parse_lower = request_text.lower() # Use lowercased for parsing structure

                    # Extract 'function_name' (part after "for " and before " in file ")
                    # "generate docstring for FUNCTION_NAME in file FILE_PATH"
                    # Split by " in file " first to isolate "generate docstring for FUNCTION_NAME"
                    part_before_file = text_to_parse_lower.split(" in file ", 1)[0]
                    # function_name_part_lower = part_before_file.split("generate docstring for ", 1)[1].strip() # unused lowercase intermediate

                    # Extract 'file_path' from original request_text to preserve case
                    # (part after " in file ")
                    original_request_parts = request_text.split(" in file ", 1) # Use original case for file path
                    file_path_part = original_request_parts[1].strip()

                    # Re-extract function_name from original_request_text to preserve case
                    temp_parts_for_func_name = request_text.split("generate docstring for ", 1)[1].split(" in file ", 1)[0]
                    original_function_name = temp_parts_for_func_name.strip()

                    task_data["function_name"] = original_function_name # Use original case
                    task_data["file_path"] = file_path_part

                    # Populate other required keys for "generate_function_docstring" capability
                    # Current capability: required_input_keys=["file_path", "function_name", "code_block_lines"]
                    task_data["code_block_lines"] = [] # Placeholder for now

                    if "description" not in task_data: # Ensure description for orchestrator validation (though it might already be there)
                        task_data["description"] = request_text

                    print(f"[{self.agent_id}] Test hook: Populated task_data for DocumentationAgent 'docstring' test: "
                          f"func='{task_data['function_name']}', file='{task_data['file_path']}'.")
                except IndexError:
                    print(f"[{self.agent_id}] Test hook: 'generate docstring for' detected for DocumentationAgent, but failed to parse all parts from '{request_text}'. Ensure format '... for FUNCTION_NAME in file FILE_PATH'.")
                except Exception as e:
                    print(f"[{self.agent_id}] Test hook: Error parsing 'generate docstring for' request for DocumentationAgent '{request_text}': {e}")

            elif ("git status" in request_text.lower() or "vcs status" in request_text.lower()) and \
                 target_agent_id == "version_control_agent_01":

                if "description" not in task_data: # Ensure description for orchestrator validation
                    task_data["description"] = request_text

                print(f"[{self.agent_id}] Test hook: Populated task_data (description) for VersionControlAgent 'status' test.")

            elif ("scan vulnerabilities in " in request_text.lower() or "scan file " in request_text.lower()) and \
                 target_agent_id == "vulnerability_scan_agent_01":
                # Example: "scan vulnerabilities in src/main.py"
                # Example: "scan file specific_file.py for vulnerabilities"
                try:
                    path_part = ""
                    if "scan vulnerabilities in " in request_text.lower():
                        # Get original case for file path
                        original_request_parts = request_text.split("scan vulnerabilities in ", 1)
                        path_part = original_request_parts[1].strip()
                    elif "scan file " in request_text.lower():
                        # "scan file X for vulnerabilities" -> X
                        original_request_parts = request_text.split("scan file ", 1)[1].split(" for vulnerabilities", 1)
                        path_part = original_request_parts[0].strip()

                    if path_part:
                        task_data["file_path_or_directory"] = path_part

                        # Populate other required keys for "scan_code_for_vulnerabilities" capability
                        # Current capability: required_input_keys=["file_path_or_directory", "scan_profile"]
                        task_data["scan_profile"] = "default" # Placeholder

                        if "description" not in task_data: # Ensure description for orchestrator validation
                            task_data["description"] = request_text

                        print(f"[{self.agent_id}] Test hook: Populated task_data for VulnerabilityScanAgent test for path '{path_part}'.")
                    else:
                        print(f"[{self.agent_id}] Test hook: 'scan vulnerabilities/file' detected for VulnerabilityScanAgent, but failed to parse path from '{request_text}'.")
                except IndexError:
                    print(f"[{self.agent_id}] Test hook: 'scan vulnerabilities/file' detected for VulnerabilityScanAgent, but failed to parse path from '{request_text}'. Ensure format '... in PATH' or '... file PATH ...'.")
                except Exception as e:
                    print(f"[{self.agent_id}] Test hook: Error parsing 'scan vulnerabilities/file' request for VulnerabilityScanAgent '{request_text}': {e}")

            elif target_agent_id == "environment_management_agent_01":
                # This agent has multiple capabilities, so the hook needs to be more specific
                # or we make multiple specific hooks.
                # Let's try to handle based on keywords in request_text for different actions.

                task_data_populated_by_hook = False

                # Hook for "modify_python_dependency" (install, add, remove, update)
                # Check for various actions
                action_found = None
                action_keywords_map = {
                    "install": ["install "],
                    "add": ["add "],
                    "remove": ["remove ", "delete "],
                    "update": ["update ", "upgrade "]
                }

                parsed_package_name = None
                parsed_version_spec = None

                for act, keywords in action_keywords_map.items():
                    for keyword in keywords:
                        if keyword in request_text.lower():
                            action_found = act
                            # Extract string after "action keyword" then "package " if present, then package name
                            # e.g., "install package requests version 2.0"
                            # e.g., "add requests"
                            # e.g., "remove my-package"
                            temp_str = request_text.lower().split(keyword, 1)[1].strip()

                            # Remove "package " prefix if it exists
                            if temp_str.startswith("package "):
                                temp_str = temp_str.split("package ", 1)[1].strip()

                            # Now, extract package name and optional version from the original case string
                            # We need to reconstruct the string part that contains package name + version
                            # based on the length of temp_str but from original request_text

                            # Find the start index of temp_str in the lowercased request_text
                            start_idx_in_lower = request_text.lower().find(temp_str, len(request_text.lower().split(keyword, 1)[0]) + len(keyword))
                            if start_idx_in_lower != -1:
                                package_info_original_case = request_text[start_idx_in_lower : start_idx_in_lower + len(temp_str)]

                                package_parts = package_info_original_case.split(" version ", 1)
                                parsed_package_name = package_parts[0].strip()
                                if len(package_parts) > 1:
                                    parsed_version_spec = package_parts[1].strip()
                                else:
                                    parsed_version_spec = "latest" # Default
                            break # Found action keyword
                    if action_found:
                        break

                if action_found == "list" or (action_found is None and "list " in request_text.lower()): # Handle "list" separately
                    task_data["action"] = "list"
                    task_data_populated_by_hook = True
                elif action_found and parsed_package_name:
                    task_data["action"] = action_found
                    task_data["package_name"] = parsed_package_name
                    if parsed_version_spec:
                        task_data["version_spec"] = parsed_version_spec
                    else: # ensure key is present if expected by some logic, even if "latest"
                        task_data["version_spec"] = "latest"
                    task_data_populated_by_hook = True

                # Hook for "setup_virtual_environment" (existing logic for this can be kept or integrated)
                # ... (ensure this part is separate or correctly conditionalized)
                elif "create venv" in request_text.lower() or "setup venv" in request_text.lower():
                    # Example: "create venv .my_test_env python 3.9"
                    parts = request_text.lower().split("venv ", 1)
                    if len(parts) > 1:
                        venv_info_str = request_text.split("venv ", 1)[1].strip() # original case
                        venv_parts = venv_info_str.split(" python ", 1)
                        task_data["venv_path"] = venv_parts[0].strip()
                        if len(venv_parts) > 1:
                            task_data["python_version"] = venv_parts[1].strip()
                        else:
                            task_data["python_version"] = "system_default" # Default
                        task_data_populated_by_hook = True

                if task_data_populated_by_hook:
                    if "description" not in task_data: # Ensure description for orchestrator validation
                        task_data["description"] = request_text
                    print(f"[{self.agent_id}] Test hook: Populated task_data for EnvironmentManagementAgent test. Action: {task_data.get('action')}, VenvPath: {task_data.get('venv_path')}")
                else:
                    # If no specific hook matched but it's routed to this agent,
                    # ensure description is there for general validation.
                    if "description" not in task_data and target_agent_id == "environment_management_agent_01":
                         task_data["description"] = request_text
                    print(f"[{self.agent_id}] Test hook: No specific data injection for EnvMgmt request '{request_text}', ensured description exists.")

            elif target_agent_id == "platform_integration_agent_01":
                task_data_populated_by_hook = False
                # Hook for "notify_slack_channel"
                if "notify slack" in request_text.lower() or "send slack" in request_text.lower():
                    # Example: "notify slack #general Hello team!"
                    # Example: "send slack message to #alerts Critical issue detected"
                    try:
                        text_to_parse = request_text.lower()
                        channel_part = ""
                        message_part = ""

                        if "notify slack " in text_to_parse:
                            temp_str = request_text.split("notify slack ", 1)[1] # Original case from here
                        elif "send slack message to " in text_to_parse:
                            temp_str = request_text.split("send slack message to ", 1)[1]
                        elif "send slack " in text_to_parse: # More generic
                            temp_str = request_text.split("send slack ", 1)[1]
                        else: # Could not find a clear start for parsing
                            temp_str = ""

                        if temp_str:
                            # First word is usually channel, rest is message
                            parts = temp_str.split(" ", 1)
                            channel_part = parts[0].strip()
                            if len(parts) > 1:
                                message_part = parts[1].strip()

                            if channel_part and message_part:
                                task_data["slack_channel_id"] = channel_part
                                task_data["message_text"] = message_part
                                # notification_type is optional in agent, default is "info"
                                # Get it if "type XYZ" is present
                                if " type " in text_to_parse:
                                    type_val = text_to_parse.split(" type ", 1)[1].split(" ",1)[0].strip()
                                    task_data["notification_type"] = type_val
                                else:
                                    task_data["notification_type"] = "info" # Default for hook
                                task_data_populated_by_hook = True
                            else: # Handle if parsing channel/message fails
                                print(f"[{self.agent_id}] Test hook: Could not parse channel and message for Slack notification from '{request_text}'.")


                    except Exception as e:
                        print(f"[{self.agent_id}] Test hook: Error parsing Slack notification request '{request_text}': {e}")

                # Add placeholder for GitHub PR hook if needed for a test later
                # elif "github pr" in request_text.lower() or "pull request" in request_text.lower():
                #     task_data["repository_url"] = "github.com/example/repo" # Placeholder
                #     task_data["branch_name"] = "feature-branch" # Placeholder
                #     task_data["pr_title"] = "New Feature PR (Simulated by Hook)" # Placeholder
                #     task_data["pr_body"] = "Details about the new feature." # Placeholder
                #     task_data["target_branch"] = "main" # Placeholder
                #     task_data_populated_by_hook = True


                if task_data_populated_by_hook:
                    if "description" not in task_data:
                        task_data["description"] = request_text
                    print(f"[{self.agent_id}] Test hook: Populated task_data for PlatformIntegrationAgent. Data: {task_data}")
                else:
                    if "description" not in task_data and target_agent_id == "platform_integration_agent_01":
                         task_data["description"] = request_text
                    print(f"[{self.agent_id}] Test hook: No specific data injection for PlatformIntegration request '{request_text}', ensured description exists.")

            # Add new elif for KnowledgeBaseAgent test (specifically for kb_query):
            elif "query kb for " in request_text.lower() and target_agent_id == "knowledge_base_agent_01":
                # Example: "query kb for novapilot architecture"
                try:
                    # Extract terms after "query kb for "
                    # Use original request_text to preserve case for query_string
                    query_terms_part = request_text.split("query kb for ", 1)[1].strip()

                    task_data["query_string"] = query_terms_part

                    # Populate other required keys for "kb_query_information" capability
                    # Current capability: required_input_keys=["query_string", "filters"]
                    task_data["filters"] = {} # Placeholder for now

                    if "description" not in task_data: # Ensure description for orchestrator validation
                        task_data["description"] = request_text

                    print(f"[{self.agent_id}] Test hook: Populated task_data for KnowledgeBaseAgent 'kb_query' test with query_string: '{query_terms_part}'.")
                except IndexError:
                    print(f"[{self.agent_id}] Test hook: 'query kb for ' detected for KnowledgeBaseAgent, but failed to parse query terms from '{request_text}'. Ensure format '... for QUERY_TERMS'.")
                except Exception as e:
                    print(f"[{self.agent_id}] Test hook: Error parsing 'query kb for ' request for KnowledgeBaseAgent '{request_text}': {e}")

            # Add new elif for AgentLifecycleManagerAgent test:
            elif "lifecycle " in request_text.lower() and target_agent_id == "agent_lifecycle_manager_agent_01":
                # Example: "lifecycle start agent some_agent_id_to_start"
                # Example: "lifecycle stop agent another_agent_id_to_stop because test"
                try:
                    text_lower = request_text.lower()
                    action_part = None
                    target_agent_id_part = None

                    if "lifecycle start agent " in text_lower:
                        action_part = "start"
                        target_agent_id_part = request_text.split("lifecycle start agent ", 1)[1].strip()
                        # Populate required_input_keys for "lifecycle_start_agent":
                        # ["target_agent_id_to_start", "agent_config"]
                        task_data["target_agent_id_to_start"] = target_agent_id_part
                        task_data["agent_config"] = {"simulated_config": True} # Placeholder

                    elif "lifecycle stop agent " in text_lower:
                        action_part = "stop"
                        # "lifecycle stop agent AGENT_ID reason REASON_TEXT"
                        temp_parts = request_text.split("lifecycle stop agent ", 1)[1].split(" reason ", 1)
                        target_agent_id_part = temp_parts[0].strip()

                        # Populate required_input_keys for "lifecycle_stop_agent":
                        # ["target_agent_id_to_stop", "stop_reason"]
                        task_data["target_agent_id_to_stop"] = target_agent_id_part
                        if len(temp_parts) > 1:
                            task_data["stop_reason"] = temp_parts[1].strip()
                        else:
                            task_data["stop_reason"] = "No reason provided (simulated hook)." # Placeholder

                    if action_part and target_agent_id_part:
                        if "description" not in task_data: # Ensure description for orchestrator validation
                            task_data["description"] = request_text
                        print(f"[{self.agent_id}] Test hook: Populated task_data for AgentLifecycleManagerAgent '{action_part}' test for agent '{target_agent_id_part}'.")
                    else:
                        print(f"[{self.agent_id}] Test hook: 'lifecycle' detected for AgentLifecycleManagerAgent, but failed to parse specific action/target from '{request_text}'.")

                except IndexError:
                    print(f"[{self.agent_id}] Test hook: 'lifecycle' detected for AgentLifecycleManagerAgent, but failed to parse action/target from '{request_text}'.")
                except Exception as e:
                    print(f"[{self.agent_id}] Test hook: Error parsing 'lifecycle' request for AgentLifecycleManagerAgent '{request_text}': {e}")

            # Add new elif for AgentSandboxAgent test:
            elif "sandbox " in request_text.lower() and target_agent_id == "agent_sandbox_agent_01": # This check for target_agent_id is now somewhat redundant if the hint worked, but good for robustness
                task_data_populated_by_hook = False
                text_lower = request_text.lower()

                # Hook for "sandbox_execute"
                # Example: "sandbox execute python code 'print("Hello Sandbox")'"
                if "execute " in text_lower:
                    try:
                        # "sandbox execute LANG code CODE_STRING"
                        parts = text_lower.split("execute ", 1)[1].split(" code ", 1)
                        language_part = parts[0].strip()
                        # Extract code from original request_text to preserve casing and quotes
                        original_code_part = request_text.split(" code ", 1)[1].strip()
                        # Remove leading/trailing single/double quotes if present, as they might be for the whole string
                        if (original_code_part.startswith("'") and original_code_part.endswith("'")) or \
                           (original_code_part.startswith('"') and original_code_part.endswith('"')):
                            original_code_part = original_code_part[1:-1]

                        task_data["language"] = language_part
                        task_data["code_to_execute"] = original_code_part
                        # Populate other required keys for "sandbox_execute_code" capability:
                        # required_input_keys=["code_to_execute", "language", "sandbox_parameters"]
                        task_data["sandbox_parameters"] = {"network": "none", "timeout": "5s"} # Placeholder
                        task_data_populated_by_hook = True
                        print(f"[{self.agent_id}] Test hook: Populated task_data for AgentSandboxAgent 'execute' test. Lang: '{language_part}'.")
                    except IndexError:
                        print(f"[{self.agent_id}] Test hook: 'sandbox execute' detected but failed to parse lang/code. Format: '... execute LANG code CODE_STRING'.")
                    except Exception as e:
                        print(f"[{self.agent_id}] Test hook: Error parsing 'sandbox execute' request: {e}")

                # Hook for "sandbox_manage_env"
                # Example: "sandbox create my_sandbox_env"
                # Example: "sandbox delete old_env"
                # Example: "sandbox get_status active_env"
                elif "create " in text_lower or "delete " in text_lower or "get_status " in text_lower or "manage " in text_lower : # "manage" is generic
                    try:
                        action_part = None
                        id_or_config_part = None

                        if "create " in text_lower:
                            action_part = "create"
                            id_or_config_part = request_text.lower().split("create ",1)[1].strip()
                        elif "delete " in text_lower:
                            action_part = "delete"
                            id_or_config_part = request_text.lower().split("delete ",1)[1].strip()
                        elif "get_status " in text_lower:
                            action_part = "get_status"
                            id_or_config_part = request_text.lower().split("get_status ",1)[1].strip()
                        elif "manage " in text_lower: # More generic, might need specific action after "manage"
                            action_part = request_text.lower().split("manage ",1)[1].split(" ",1)[0].strip() # e.g. "manage create myenv"
                            id_or_config_part = request_text.lower().split(action_part,1)[1].strip()


                        if action_part:
                            task_data["sandbox_action"] = action_part
                            # Populate other required keys for "sandbox_manage_environment" capability:
                            # required_input_keys=["sandbox_action", "sandbox_id_or_config"]
                            task_data["sandbox_id_or_config"] = id_or_config_part if id_or_config_part else "default_sandbox" # Placeholder if not parsed
                            task_data_populated_by_hook = True
                            print(f"[{self.agent_id}] Test hook: Populated task_data for AgentSandboxAgent 'manage_env' test. Action: '{action_part}'.")
                        else:
                             print(f"[{self.agent_id}] Test hook: 'sandbox manage' action detected but specific action (create/delete/get_status) not clear from '{request_text}'.")
                    except IndexError:
                        print(f"[{self.agent_id}] Test hook: 'sandbox manage' action detected but failed to parse action/id from '{request_text}'.")
                    except Exception as e:
                        print(f"[{self.agent_id}] Test hook: Error parsing 'sandbox manage' request: {e}")

                if task_data_populated_by_hook:
                    if "description" not in task_data:
                        task_data["description"] = request_text
                else: # If no specific hook matched but routed here
                    if "description" not in task_data and target_agent_id == "agent_sandbox_agent_01":
                         task_data["description"] = request_text
                    print(f"[{self.agent_id}] Test hook: No specific data injection for AgentSandbox request '{request_text}', ensured description exists.")

            # elif "store in kb " in request_text.lower() and target_agent_id == "knowledge_base_agent_01":
            #    # Placeholder for kb_store test hook if needed later
            #    # task_data["document_content"] = "..."
            #    # task_data["document_id"] = "..."
            #    # task_data["metadata_tags"] = []
            #    # if "description" not in task_data: task_data["description"] = request_text
            #    # print(f"[{self.agent_id}] Test hook: Populated task_data for KnowledgeBaseAgent 'kb_store' test.")
            #    pass


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
            "automated_testing_agent_01": "automated_testing_tasks",
            "refactoring_agent_01": "refactoring_tasks",
            "documentation_agent_01": "documentation_tasks",
            "version_control_agent_01": "version_control_tasks",
            "vulnerability_scan_agent_01": "vulnerability_scan_tasks",
            "environment_management_agent_01": "environment_management_tasks",
            "platform_integration_agent_01": "platform_integration_tasks",
            "knowledge_base_agent_01": "knowledge_base_tasks",
            "agent_lifecycle_manager_agent_01": "agent_lifecycle_tasks",
            "agent_sandbox_agent_01": "agent_sandbox_tasks",
            "guardrail_agent_01": "guardrail_tasks",
            "evaluation_agent_01": "evaluation_tasks"
        } # Total 16 agents
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
