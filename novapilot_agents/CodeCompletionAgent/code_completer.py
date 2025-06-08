# novapilot_agents/CodeCompletionAgent/code_completer.py
import asyncio
from typing import Optional, Any, Callable, Dict, List

from novapilot_core.aci import AgentCommunicationInterface
from novapilot_core.models import Task, ExecutionResult, AgentCapability, ProjectContext
from novapilot_core.message_bus import message_bus

class CodeCompletionAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._task_queue: Optional[asyncio.Queue] = None
        self._discovery_queue: Optional[asyncio.Queue] = None
        self._listener_tasks: List[asyncio.Task] = []
        self._project_context_cache: Optional[ProjectContext] = None # Optional: if needed

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def _get_project_context(self) -> Optional[ProjectContext]:
        # Basic implementation if needed, similar to CodeUnderstandingAgent
        # For now, can be a placeholder or not used if completion doesn't need deep project context initially
        if self._project_context_cache:
            return self._project_context_cache
        # Simplified: Assume not immediately needed or fetched elsewhere if critical
        print(f"[{self.agent_id}] _get_project_context called (placeholder - not fetching).")
        return None

    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received CodeCompletion task: {task.description}, Type: {task.task_type}, Data: {task.data}")

        code_context = str(task.data.get("code_context", "")).lower() # Ensure lowercase for matching
        # file_path = task.data.get("file_path") # For future use
        # cursor_position = task.data.get("cursor_position") # For future use

        completions = []
        status = "completed" # Assume task completes, even if no suggestions
        output_message = "No specific completion trigger found in code_context."
        result_data_content = {"completions_list": []}

        if "def " in code_context: # Check for "def " (with a space)
            completions = [
                "def function_name(params):",
                "    pass",
                "    return None"
            ]
            output_message = "Provided basic Python function definition snippets."
            result_data_content["completions_list"] = completions
            print(f"[{self.agent_id}] 'def ' detected. Providing function snippets.")

        # Add more elif blocks here for other simple triggers if desired in future.
        # elif "class " in code_context:
        #     completions = ["class ClassName:", "    def __init__(self):", "        pass"]
        #     output_message = "Provided basic Python class definition snippets."
        #     result_data_content["completions_list"] = completions
        #     print(f"[{self.agent_id}] 'class ' detected. Providing class snippets.")

        result = ExecutionResult(
            task_id=task.task_id,
            status=status,
            output=output_message,
            data=result_data_content
        )

        if task.source_agent_id:
            result_channel = f"task_results_{task.source_agent_id}"
            await self._message_bus.publish(result_channel, result)
            print(f"[{self.agent_id}] Published completion result for task {task.task_id} to {result_channel}. Completions: {len(completions)}")
        else:
            print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id. Cannot publish result.")

    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                capability_id="provide_code_completions",
                task_type="code_completion_provide_suggestions",
                description="Provides code completion suggestions based on current code context and cursor position.",
                keywords=["code", "completion", "suggest", "autocomplete", "intellisense", "complete", "python", "def", "snippet"],
                required_input_keys=["code_context", "cursor_position", "file_path"], # Example keys
                generates_output_keys=["completions_list"] # Example key
            )
        ]

    async def _task_listener_loop(self):
        channel_name = "code_completion_tasks" # Specific task channel
        self._task_queue = await self._message_bus.subscribe(channel_name)
        print(f"[{self.agent_id}] Subscribed to '{channel_name}'. Listening for tasks...")
        try:
            while True:
                message = await self._task_queue.get()
                if isinstance(message, Task):
                    if message.target_agent_id == self.agent_id or message.target_agent_id is None:
                        asyncio.create_task(self._process_task(message))
                    # else: ignore task not for this agent
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
        task_channel_name = "code_completion_tasks"
        discovery_channel_name = "system_discovery_channel"
        await self._message_bus.publish(task_channel_name, f"stop_listening_{task_channel_name}")
        await self._message_bus.publish(discovery_channel_name, f"stop_listening_{discovery_channel_name}")

        # Wait for tasks to complete or be cancelled
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
    async def post_task(self, task: Task) -> bool: # Should not be called on self typically
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
