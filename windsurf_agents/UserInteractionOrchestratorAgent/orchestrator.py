# windsurf_agents/UserInteractionOrchestratorAgent/orchestrator.py
import asyncio
import uuid # For generating unique task IDs
from typing import Dict, Optional, Any, Callable # Ensure these are imported

from windsurf_core.aci import AgentCommunicationInterface
from windsurf_core.models import Task, ExecutionResult # Make sure ExecutionResult is imported
from windsurf_core.message_bus import message_bus

class UserInteractionOrchestratorAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._active_tasks: Dict[str, Task] = {}
        self._task_results_queue: Optional[asyncio.Queue] = None

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

    async def start_listening(self):
        # Start all background listening tasks for this agent
        asyncio.create_task(self._listen_for_results())

    async def stop_listening(self):
        # Signal all background listening tasks to stop
        results_channel = f"task_results_{self.agent_id}"
        await self._message_bus.publish(results_channel, "stop_listening")


    async def receive_user_request(self, request_text: str, target_agent_id: Optional[str] = None, task_data: Optional[Dict[str, Any]] = None):
        task_id = str(uuid.uuid4())
        if task_data is None:
            task_data = {} # Initialize if None

        # Simple keyword-based routing for demonstration
        # In a real system, this would use more sophisticated NLP or command parsing.
        actual_target_agent_id = target_agent_id
        task_description = request_text

        if request_text.lower().startswith("read file ") or request_text.lower().startswith("analyze file "):
            parts = request_text.split(" ", 2)
            if len(parts) > 2:
                file_path = parts[2]
                task_data["file_path"] = file_path
                actual_target_agent_id = "code_understanding_agent_01"
                task_description = f"Analyze file: {file_path}" # Standardize description
                print(f"[{self.agent_id}] Identified file analysis request for: {file_path}")
            else:
                print(f"[{self.agent_id}] File analysis request received, but file path seems missing: {request_text}")
                # Let it proceed, it might be a generic task or fail at the target
        elif target_agent_id is None: # Default to codegen if no specific target and not a file read
            actual_target_agent_id = "codegen_agent_01"


        if actual_target_agent_id is None:
            print(f"[{self.agent_id}] Could not determine target agent for request: {request_text}")
            # Optionally create a failed task here or return None
            return None


        task = Task(
            task_id=task_id,
            description=task_description,
            source_agent_id=self.agent_id,
            target_agent_id=actual_target_agent_id,
            data=task_data,
            status="pending_dispatch"
        )
        self._active_tasks[task_id] = task
        print(f"[{self.agent_id}] New task created: {task_id} for agent {actual_target_agent_id} - {task.description}")

        await self.post_task(task)
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
