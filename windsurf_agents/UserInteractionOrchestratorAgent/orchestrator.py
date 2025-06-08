# windsurf_agents/UserInteractionOrchestratorAgent/orchestrator.py
import asyncio
import uuid # For generating unique task IDs
from typing import Dict, Optional, Any, Callable, List # Add List

from windsurf_core.aci import AgentCommunicationInterface
from windsurf_core.models import Task, ExecutionResult, AgentCapability # Add AgentCapability
from windsurf_core.message_bus import message_bus

class UserInteractionOrchestratorAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._active_tasks: Dict[str, Task] = {}
        self._task_results_queue: Optional[asyncio.Queue] = None
        self._agent_capabilities_registry: Dict[str, List[AgentCapability]] = {}
        self._known_agent_ids: List[str] = ["codegen_agent_01", "code_understanding_agent_01"] # Example
        self._discovery_response_queue: Optional[asyncio.Queue] = None

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
                    print(f"[{self.agent_id}] Received result for task {result.task_id}: {result.status} - {result.output}")
                    if result.task_id in self._active_tasks:
                        self._active_tasks[result.task_id].status = result.status
                        # Potentially store the full result or notify other parts of the system
                    else:
                        print(f"[{self.agent_id}] Warning: Received result for unknown task ID {result.task_id}")
                elif result == "stop_listening":
                    print(f"[{self.agent_id}] Stop signal received for results listener.")
                    break
                self._task_results_queue.task_done() # Important for queue management if using join()
        except Exception as e:
            print(f"[{self.agent_id}] Error in results listener: {e}")
        finally:
            if self._task_results_queue:
                await self._message_bus.unsubscribe(results_channel, self._task_results_queue)
            print(f"[{self.agent_id}] Unsubscribed and stopped listening for results.")

    async def _listen_for_discovery_responses(self):
        discovery_channel = f"orchestrator_discovery_responses_{self.agent_id}"
        self._discovery_response_queue = await self._message_bus.subscribe(discovery_channel)
        print(f"[{self.agent_id}] Subscribed to '{discovery_channel}' for agent capability responses.")
        try:
            while True:
                response = await self._discovery_response_queue.get()
                if isinstance(response, dict) and response.get("type") == "agent_capabilities_response":
                    agent_id = response.get("agent_id")
                    capabilities_data = response.get("capabilities")
                    if agent_id and capabilities_data:
                        # Assuming capabilities_data is a list of dicts, need to deserialize to AgentCapability objects
                        # For now, if AgentCapability is complex, this might need adjustment
                        # or ensure AgentCapability is simple enough (like a dataclass that serializes well)
                        # For this step, let's assume it's a list of AgentCapability objects directly if message_bus handles objects.
                        # If message_bus serializes to JSON, then this needs proper deserialization.
                        # For simplicity, we'll assume the message bus passes Python objects directly for now.

                        # Convert dictionaries back to AgentCapability objects if necessary
                        # This part is crucial if the message bus serializes/deserializes.
                        # If it just passes Python objects, this might be simpler.
                        # Let's assume for now that the objects are passed as-is or easily convertible.
                        # A more robust solution would involve explicit serialization/deserialization logic.

                        # capabilities_data should be List[AgentCapability] as sent by other agents
                        if isinstance(capabilities_data, list) and all(isinstance(cap, AgentCapability) for cap in capabilities_data):
                            self._agent_capabilities_registry[agent_id] = capabilities_data
                            print(f"[{self.agent_id}] Received and registered capabilities from {agent_id}: {len(capabilities_data)} capabilities.")
                        else:
                            # This case would occur if the message bus or sending agent did not adhere to passing AgentCapability objects.
                            # For example, if it sent list of dicts that need deserialization.
                            print(f"[{self.agent_id}] Received capabilities_data from {agent_id} not in expected List[AgentCapability] format. Data: {capabilities_data}")
                            # Optionally, attempt deserialization if it's a known format like list of dicts:
                            # try:
                            #     capabilities = [AgentCapability(**cap_dict) for cap_dict in capabilities_data]
                            #     self._agent_capabilities_registry[agent_id] = capabilities
                            #     print(f"[{self.agent_id}] Successfully deserialized and registered capabilities from {agent_id}: {len(capabilities)}.")
                            # except Exception deserialization_error:
                            #     print(f"[{self.agent_id}] Failed to deserialize capabilities_data from {agent_id}: {deserialization_error}. Data: {capabilities_data}")
                elif response == "stop_listening_discovery":
                    print(f"[{self.agent_id}] Stop signal received for discovery responses listener.")
                    break
                else:
                    print(f"[{self.agent_id}] Received malformed/unexpected message on discovery response channel: {response}")
                if self._discovery_response_queue: # Check queue exists
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
        # Clear previous registry before discovery
        self._agent_capabilities_registry.clear()

        for agent_id in self._known_agent_ids:
            # In a more advanced system, agents might have their own inbox channels.
            # For now, publishing to a general discovery channel they all listen to.
            print(f"[{self.agent_id}] Requesting capabilities from potential agent {agent_id} on 'system_discovery_channel'.")
            await self._message_bus.publish("system_discovery_channel", discovery_request)

        # Add a small delay to allow agents to respond. This is a simple mechanism.
        # A more robust system might use acknowledgements or a timeout for responses.
        await asyncio.sleep(1.0) # Wait for responses
        print(f"[{self.agent_id}] Agent discovery attempt finished. Registry: {self._agent_capabilities_registry}")

    async def start_listening(self):
        # Start all background listening tasks for this agent
        asyncio.create_task(self._listen_for_results())
        asyncio.create_task(self._listen_for_discovery_responses()) # Add this line

    async def stop_listening(self):
        # Signal all background listening tasks to stop
        results_channel = f"task_results_{self.agent_id}"
        await self._message_bus.publish(results_channel, "stop_listening")
        discovery_channel = f"orchestrator_discovery_responses_{self.agent_id}"
        await self._message_bus.publish(discovery_channel, "stop_listening_discovery") # Add this line


    async def receive_user_request(self, request_text: str, task_data: Optional[Dict[str, Any]] = None):
        task_id = str(uuid.uuid4())
        if task_data is None:
            task_data = {}

        print(f"[{self.agent_id}] New user request received: '{request_text}'")

        # Simple keyword extraction from request_text (lowercase, split by space)
        request_keywords = set(request_text.lower().split())
        # In a more advanced system, use NLP for better keyword extraction & stop word removal.

        best_match_agent_id = None
        highest_score = 0
        best_capability_description = "" # For logging/debugging

        if not self._agent_capabilities_registry:
            print(f"[{self.agent_id}] Warning: Agent capabilities registry is empty. Cannot perform smart routing. Consider running discover_agents().")
            # Fallback or error handling if registry is empty. For now, we'll let it try to find a match (which will fail).

        for agent_id, capabilities in self._agent_capabilities_registry.items():
            for capability in capabilities:
                # Simple score: number of matching keywords
                # Ensure capability.keywords are also lowercase for consistent matching, or handle case during registration.
                # For now, assuming they are registered in a consistent case (e.g. lowercase) or we convert here.
                capability_keywords = set(k.lower() for k in capability.keywords)
                common_keywords = request_keywords.intersection(capability_keywords)
                score = len(common_keywords)

                # Basic tie-breaking: prefer more specific capabilities (more keywords defined)
                # This is very rudimentary.
                if score > highest_score:
                    highest_score = score
                    best_match_agent_id = agent_id
                    best_capability_description = capability.description
                elif score == highest_score and score > 0:
                    # If scores are equal, prefer the one with more keywords in its definition (more specific)
                    # This is a simplistic tie-breaker. Could also consider capability priority if added.
                    current_best_keywords_len = 0
                    for cap_list in self._agent_capabilities_registry.get(best_match_agent_id, []):
                        if cap_list.description == best_capability_description: # find the current best capability
                            current_best_keywords_len = len(cap_list.keywords)
                            break

                    if len(capability.keywords) > current_best_keywords_len:
                        best_match_agent_id = agent_id
                        best_capability_description = capability.description


        target_agent_id = best_match_agent_id
        task_status = "pending_dispatch"
        final_task_description = request_text # Use original request as description

        if target_agent_id:
            print(f"[{self.agent_id}] Smart routing determined target: {target_agent_id} (Capability: '{best_capability_description}' with score {highest_score}) for request: '{request_text}'")
            # If the chosen capability implies specific data needs, update task_data here.
            # For example, if it's a file analysis task, ensure file_path is extracted and put in task_data.
            # This part needs to be coordinated with how capabilities define their data requirements.
            # For now, we'll assume the CodeUnderstandingAgent's capability keywords are good enough
            # and the orchestrator can still manually add file_path for such tasks if needed,
            # or the task description itself contains the file path.

            # Example: If routing to CodeUnderstandingAgent, ensure file_path is in task_data
            # This is still a bit manual and could be improved by capabilities defining input data structure.
            if target_agent_id == "code_understanding_agent_01":
                # Attempt to extract file_path if not already in task_data
                if "file_path" not in task_data:
                    # A very basic way to get a file path if the request text contains it
                    # e.g. "analyze file my_file.py"
                    words = request_text.lower().split()
                    if "file" in words and words.index("file") + 1 < len(words):
                        # Check if the word after "file" looks like a path/filename
                        # Corrected index from +2 to +1
                        potential_path = request_text.split()[words.index("file") + 1] # Get original case word
                        # This is very naive, just for demonstration
                        if "." in potential_path or "/" in potential_path or "\\" in potential_path:
                             task_data["file_path"] = potential_path
                             final_task_description = f"Analyze file: {potential_path}"


        else:
            task_status = "unroutable"
            print(f"[{self.agent_id}] Could not find a suitable agent for request: '{request_text}'. Marked as unroutable.")
            # No target_agent_id, so post_task will fail or skip.

        task = Task(
            task_id=task_id,
            description=final_task_description, # Use potentially modified description
            source_agent_id=self.agent_id,
            target_agent_id=target_agent_id, # This can be None if unroutable
            data=task_data,
            status=task_status
        )
        self._active_tasks[task_id] = task
        print(f"[{self.agent_id}] New task created: {task_id} for agent {target_agent_id if target_agent_id else 'N/A'} - {task.description}")

        if task.status == "pending_dispatch" and task.target_agent_id:
            await self.post_task(task)
        elif not task.target_agent_id and task.status == "unroutable":
            print(f"[{self.agent_id}] Task {task.task_id} is unroutable and will not be posted.")
            # Optionally, publish an event or log this unroutable task for monitoring

        return task_id

    # --- ACI Implementation ---
    async def send_message(self, target_agent_id: str, message_content: Any, message_type: str = "generic") -> bool:
        print(f"[{self.agent_id}] send_message: Type '{message_type}' to {target_agent_id} (stub)")
        # Actual implementation would use message_bus.publish to a specific channel for that agent
        await self._message_bus.publish(f"agent_messages_{target_agent_id}", message_content)
        return True

    async def receive_message(self) -> Optional[Any]:
        # This agent primarily uses specific listeners (like _listen_for_results)
        # rather than a generic receive_message polling.
        print(f"[{self.agent_id}] receive_message called (stub - use specific listeners)")
        return None

    async def post_task(self, task: Task) -> bool:
        if not task.target_agent_id:
            print(f"[{self.agent_id}] Task {task.task_id} has no target_agent_id. Cannot post.")
            return False

        # Determine the channel based on the target agent or task type
        # This is a simplified routing mechanism.
        channel_map = {
            "codegen_agent_01": "code_generation_tasks",
            "code_understanding_agent_01": "code_understanding_tasks" # New entry
            # Add other agent_id to channel mappings here
        }

        target_channel = channel_map.get(task.target_agent_id)

        if target_channel:
            task.status = "dispatched"
            print(f"[{self.agent_id}] Posting task {task.task_id} to {task.target_agent_id} on channel '{target_channel}': {task.description}")
            await self._message_bus.publish(target_channel, task)
            # Store or update the task in active_tasks if not already there by receive_user_request
            if task.task_id not in self._active_tasks:
                 self._active_tasks[task.task_id] = task
            else: # Update existing task status
                 self._active_tasks[task.task_id].status = "dispatched"
            return True
        else:
            print(f"[{self.agent_id}] No channel configured for target agent ID: {task.target_agent_id}")
            if task.task_id in self._active_tasks:
                self._active_tasks[task.task_id].status = "dispatch_failed"
            return False

    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[ExecutionResult]:
        # This is a simplified direct retrieval. In a real system, this might wait for an event
        # or check a data store where results are placed.
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            print(f"[{self.agent_id}] Checking result for task {task_id}. Current status: {task.status}")
            if task.status == "completed" or task.status == "failed":
                # This assumes the result is stored within the task object or a related structure.
                # For this example, we don't have the ExecutionResult directly stored here yet after _listen_for_results
                # This part needs to be coordinated with how _listen_for_results stores the actual ExecutionResult object.
                # For now, returning a mock ExecutionResult if task is marked completed.
                if task.status == "completed":
                    return ExecutionResult(task_id=task_id, status="completed", output="Mock result from orchestrator")
                else:
                    return ExecutionResult(task_id=task_id, status="failed", error_message="Mock failure from orchestrator")
            # If timeout is implemented, here you would wait.
        return None

    def register_event_listener(self, event_type: str, callback: Callable[[Any], None]) -> bool:
        # This would involve subscribing to a specific channel on the message bus
        # and associating the callback. For simplicity, we're using dedicated listeners for now.
        print(f"[{self.agent_id}] register_event_listener for '{event_type}' (stub)")
        # Example: asyncio.create_task(self._generic_listener(event_type, callback))
        return True

    async def emit_event(self, event_type: str, event_data: Any) -> bool:
        print(f"[{self.agent_id}] Emitting event '{event_type}' (stub)")
        await self._message_bus.publish(event_type, event_data)
        return True

    async def get_capabilities(self) -> List[AgentCapability]:
        # The orchestrator itself might not have capabilities to be discovered for task execution,
        # as its primary role is to route tasks to other agents.
        # However, it must implement the method from the ACI.
        # Returning an empty list or a capability describing its orchestration role.
        # For now, returning empty as it doesn't execute tasks based on keywords itself.
        return []
