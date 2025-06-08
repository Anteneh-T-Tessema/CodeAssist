# novapilot_agents/CodeGenerationAgent/generator.py # Corrected path in comment
import asyncio
from typing import Optional, Any, Callable, Dict, List # Ensure List is here
from novapilot_core.aci import AgentCommunicationInterface # Corrected import
from novapilot_core.models import Task, ExecutionResult, AgentCapability # Corrected import
from novapilot_core.message_bus import message_bus # Corrected import

class CodeGenerationAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._task_queue: Optional[asyncio.Queue] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received task: {task.description}, TaskType: {task.task_type}, Data: {task.data}")

        target_file_path = task.data.get("target_file_path")
        # Get 'target_file_is_editable'. If key is missing, default to True.
        # Only an explicit False value for 'target_file_is_editable' will trigger the block.
        target_file_is_editable = task.data.get("target_file_is_editable", True)

        if target_file_path is not None and target_file_is_editable is False:
            error_message = f"Target file '{target_file_path}' is not marked as editable."
            print(f"[{self.agent_id}] Task {task.task_id} failed pre-check: {error_message}")

            result_data_dict = {
                "target_file_path": target_file_path,
                "editable_check_failed": True,
                "original_request_description": task.description
            }

            result = ExecutionResult(
                task_id=task.task_id,
                status="failed",
                output=error_message,
                error_message=error_message,
                data=result_data_dict
            )

            if task.source_agent_id:
                result_channel = f"task_results_{task.source_agent_id}"
                print(f"[{self.agent_id}] Publishing result for task {task.task_id} to '{result_channel}'.")
                await self._message_bus.publish(result_channel, result)
            else:
                print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id. Cannot publish result for editable check failure.")
            return # Important: Exit early

        # --- Existing code generation logic continues below if the above check passes ---
        print(f"[{self.agent_id}] Processing task ID: {task.task_id} for actual code generation (editable check passed or not applicable).")

        generated_code = None
        error_message_for_generation = None
        status = "completed"

        # Enhanced code generation logic using task.task_type and task.description
        if task.task_type == "code_generation_python_hello_world" or        ("hello world function in python" in task.description.lower()) or        ("hello novapilot" in task.description.lower()):
            generated_code = (
                "def greet():\n"
                "    print(\"Hello, NovaPilot!\")\n"
                "\n"
                "greet()"
            )
        elif task.task_type == "code_generation_python_sum" or          ("sum function" in task.description.lower()):
            generated_code = (
                "def sum_two_numbers(a, b):\n"
                "    return a + b\n"
            )
        elif task.task_type == "code_generation_python_general": # General python code generation
            generated_code = f"# Code for: {task.description}\npass # Placeholder for general Python code"
        else:
            status = "failed"
            error_message_for_generation = f"Unsupported code generation request. Task description: '{task.description}', Task type: '{task.task_type}' did not match any known patterns."
            print(f"[{self.agent_id}] Task {task.task_id} failed generation: {error_message_for_generation}")

        # --- Construct final ExecutionResult for the generation part ---
        current_data = {}
        output_summary = ""

        if status == "completed" and generated_code:
            current_data["generated_code_string"] = generated_code
            output_summary = f"Successfully generated code for: {task.description}"
            if target_file_path:
                output_summary += f" (intended for {target_file_path})"
                current_data["target_file_path"] = target_file_path
        elif status == "failed":
            output_summary = error_message_for_generation if error_message_for_generation else "Code generation failed for an unknown reason."
            if target_file_path: # Still include target_file_path in data even if generation failed
                current_data["target_file_path"] = target_file_path
                current_data["generation_failed_for_target"] = True


        generation_result = ExecutionResult(
            task_id=task.task_id,
            status=status,
            output=output_summary,
            error_message=error_message_for_generation if status == "failed" else None,
            data=current_data,
            artifacts=[]
        )

        if task.source_agent_id:
            result_channel = f"task_results_{task.source_agent_id}"
            print(f"[{self.agent_id}] Publishing generation result for task {task.task_id} to '{result_channel}'.")
            await self._message_bus.publish(result_channel, generation_result)
        else:
            print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id. Cannot publish generation result.")

    async def start_listening(self):
        # Agent now listens to two types of messages: its own tasks and discovery requests
        # For simplicity, we'll use two queues by subscribing twice.
        # A more advanced agent might have one queue and route based on message content.

        self._task_queue = await self._message_bus.subscribe("code_generation_tasks")
        discovery_queue = await self._message_bus.subscribe("system_discovery_channel") # New subscription

        print(f"[{self.agent_id}] Subscribed to 'code_generation_tasks' and 'system_discovery_channel'. Listening...")

        async def task_listener_loop():
            try:
                while True:
                    message = await self._task_queue.get()
                    if isinstance(message, Task):
                        if message.target_agent_id == self.agent_id or message.target_agent_id is None:
                            asyncio.create_task(self._process_task(message))
                        else:
                            print(f"[{self.agent_id}] Received task {message.task_id} not for this agent. Ignoring.")
                    elif message == "stop_listening_tasks": # Specific stop for this loop
                        print(f"[{self.agent_id}] Stop signal received for task listener.")
                        break
                    else:
                        print(f"[{self.agent_id}] Received non-Task message on tasks channel: {message}")
                    if self._task_queue: self._task_queue.task_done()
            finally:
                if self._task_queue:
                    await self._message_bus.unsubscribe("code_generation_tasks", self._task_queue)
                print(f"[{self.agent_id}] Unsubscribed and stopped listening for tasks.")

        async def discovery_listener_loop():
            try:
                while True:
                    message = await discovery_queue.get()
                    if isinstance(message, dict) and message.get("type") == "request_capabilities":
                        response_channel = message.get("response_channel")
                        if response_channel:
                            print(f"[{self.agent_id}] Received capability request. Responding on {response_channel}.")
                            capabilities = await self.get_capabilities()
                            # Convert AgentCapability objects to dicts for sending if message bus requires JSON
                            # For now, assume message bus handles Python objects.
                            # capabilities_data = [vars(cap) for cap in capabilities] # Example if dicts are needed
                            capabilities_data = capabilities # Assuming objects are fine

                            await self._message_bus.publish(response_channel, {
                                "type": "agent_capabilities_response",
                                "agent_id": self.agent_id,
                                "capabilities": capabilities_data
                            })
                    elif message == "stop_listening_discovery_system": # Specific stop for this loop
                        print(f"[{self.agent_id}] Stop signal received for system discovery listener.")
                        break
                    if discovery_queue: discovery_queue.task_done()
            finally:
                if discovery_queue:
                    await self._message_bus.unsubscribe("system_discovery_channel", discovery_queue)
                print(f"[{self.agent_id}] Unsubscribed and stopped listening on system_discovery_channel.")

        # Store tasks to be gathered
        self._listener_tasks = [
            asyncio.create_task(task_listener_loop()),
            asyncio.create_task(discovery_listener_loop())
        ]
        # Wait for all listener tasks to complete (e.g., if stop_listening is called)
        # This part is tricky; start_listening usually doesn't block.
        # The waiting for completion should happen after stop_listening is called.
        # For now, just launching them.

    async def stop_listening(self):
        print(f"[{self.agent_id}] Requesting to stop listening.")
        await self._message_bus.publish("code_generation_tasks", "stop_listening_tasks")
        await self._message_bus.publish("system_discovery_channel", "stop_listening_discovery_system")
        # Add logic here to await self._listener_tasks if they were stored
        if hasattr(self, '_listener_tasks') and self._listener_tasks:
            await asyncio.gather(*self._listener_tasks, return_exceptions=True)
            print(f"[{self.agent_id}] All listener tasks gathered.")


    # --- ACI Implementation (Stubs - can be filled later if needed) ---
    async def send_message(self, target_agent_id: str, message_content: Any, message_type: str = "generic") -> bool:
        print(f"[{self.agent_id}] send_message called (stub)")
        # Example: await self._message_bus.publish(f"agent_messages_{target_agent_id}", message_content)
        return True

    async def receive_message(self) -> Optional[Any]:
        print(f"[{self.agent_id}] receive_message called (stub - use specific listeners)")
        return None

    async def post_task(self, task: Task) -> bool:
        # This agent primarily receives tasks via its subscribed channel
        print(f"[{self.agent_id}] post_task called (stub) - this agent receives tasks via subscription.")
        if task.target_agent_id == self.agent_id:
            # Optionally, could put into its own queue if not using direct listen_for_tasks
            # For now, just acknowledge if it were to be used.
            print(f"[{self.agent_id}] Task {task.task_id} could be processed if direct posting was primary.")
            return True
        return False

    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[ExecutionResult]:
        print(f"[{self.agent_id}] get_task_result called (stub)")
        # Results are proactively published; direct retrieval by others is not the primary model here.
        return None

    def register_event_listener(self, event_type: str, callback: Callable[[Any], None]) -> bool:
        print(f"[{self.agent_id}] register_event_listener for '{event_type}' (stub)")
        return True

    async def emit_event(self, event_type: str, event_data: Any) -> bool:
        print(f"[{self.agent_id}] Emitting event '{event_type}' (stub)")
        await self._message_bus.publish(event_type, event_data)
        return True

    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                capability_id="generate_python_code_general",
                task_type="code_generation_python", # Made task_type more specific
                description="Generates Python code snippets based on natural language descriptions.",
                keywords=["generate", "code", "python", "script", "function", "class", "write"],
                required_input_keys=["description"], # Expects general description in Task.description
                generates_output_keys=["generated_code_string"]
            ),
            AgentCapability(
                capability_id="generate_python_hello_world",
                task_type="code_generation_python_hello_world",
                description="Generates a 'Hello, NovaPilot!' Python function.", # Changed here
                keywords=["hello", "world", "greet", "print", "simple"],
                required_input_keys=[], # Description is enough, or can be implied by keywords
                generates_output_keys=["generated_code_string"]
            ),
            AgentCapability(
                capability_id="generate_python_sum_function",
                task_type="code_generation_python_sum",
                description="Generates a Python function to sum two numbers.",
                keywords=["sum", "add", "numbers", "calculator", "math"],
                required_input_keys=[], # Description is enough
                generates_output_keys=["generated_code_string"]
            )
        ]
