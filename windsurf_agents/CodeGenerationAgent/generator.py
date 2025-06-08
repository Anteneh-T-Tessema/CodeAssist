# windsurf_agents/CodeGenerationAgent/generator.py
import asyncio
from typing import Optional, Any, Callable, Dict, List # Ensure List is here
from windsurf_core.aci import AgentCommunicationInterface
from windsurf_core.models import Task, ExecutionResult, AgentCapability # Add AgentCapability
from windsurf_core.message_bus import message_bus

class CodeGenerationAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._task_queue: Optional[asyncio.Queue] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received task: {task.description}")
        print(f"[{self.agent_id}] Processing task ID: {task.task_id} from {task.source_agent_id}...")
        await asyncio.sleep(0.5) # Simulate work

        generated_code = None
        error_message = None
        status = "completed"

        # Simple simulation of code generation based on task description
        if "hello world function in python" in task.description.lower():
            generated_code = (
                "def greet():\n"
                "    print(\"Hello, Windsurf!\")\n"
                "\n"
                "greet()"
            )
        elif "sum function" in task.description.lower():
            generated_code = (
                "def sum_two_numbers(a, b):\n"
                "    return a + b\n"
            )
        else:
            status = "failed"
            error_message = "Unsupported code generation request or unclear task description."
            print(f"[{self.agent_id}] Task {task.task_id} failed: {error_message}")


        result_data = ExecutionResult(
            task_id=task.task_id,
            status=status,
            output=generated_code if generated_code else error_message, # Put code or error in output
            error_message=error_message if status == "failed" else None,
            artifacts=[] # Could add file path if code was written to a file
        )

        # Publish result to the orchestrator's result channel
        result_channel = f"task_results_{task.source_agent_id}"
        print(f"[{self.agent_id}] Task {task.task_id} processing finished. Status: {status}. Publishing result to '{result_channel}'.")
        await self._message_bus.publish(result_channel, result_data)

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
                task_type="code_generation",
                description="Generates Python code snippets based on natural language descriptions.",
                keywords=["generate", "code", "create", "function", "python", "script", "write"] # Atomized
            ),
            AgentCapability(
                capability_id="generate_python_hello_world",
                task_type="code_generation",
                description="Generates a 'Hello, Windsurf!' Python function.",
                keywords=["hello", "world", "greet", "function", "simple", "print"] # Atomized
            ),
            AgentCapability(
                capability_id="generate_python_sum_function",
                task_type="code_generation",
                description="Generates a Python function to sum two numbers.",
                keywords=["sum", "function", "add", "numbers", "calculator"] # Atomized
            )
        ]
