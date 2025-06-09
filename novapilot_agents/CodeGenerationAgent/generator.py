# novapilot_agents/CodeGenerationAgent/generator.py
import asyncio
import os # Added
import uuid # Added
from typing import Optional, Any, Callable, Dict, List
from novapilot_core.aci import AgentCommunicationInterface
from novapilot_core.models import Task, ExecutionResult, AgentCapability, ProjectContext
from novapilot_core.message_bus import message_bus

class CodeGenerationAgent(AgentCommunicationInterface):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._task_queue: Optional[asyncio.Queue] = None
        self._discovery_queue: Optional[asyncio.Queue] = None # Added for consistency
        self._listener_tasks: List[asyncio.Task] = []      # Added for consistency
        self._project_context_cache: Optional[ProjectContext] = None # Added for _get_project_context

    @property
    def agent_id(self) -> str:
        return self._agent_id

    # Added _get_project_context for consistency and potential use by _process_task
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
        print(f"[{self.agent_id}] Received task: {task.description}, Type: {task.task_type}, Data: {task.data}")

        target_file_path = task.data.get("target_file_path")
        target_file_is_editable = task.data.get("target_file_is_editable", True)

        if target_file_path is not None and target_file_is_editable is False:
            error_message = f"Target file '{target_file_path}' is not marked as editable. Code generation for file aborted."
            print(f"[{self.agent_id}] Task {task.task_id} failed pre-check: {error_message}")
            result_data_content = {
                "target_file_path": target_file_path,
                "editable_check_failed": True,
                "original_request_description": task.description,
                "generated_code_string": None # No code generated due to pre-check failure
            }
            result = ExecutionResult(task_id=task.task_id, status="failed", output=error_message, error_message=error_message, data=result_data_content)
            # ... (publish result logic as before) ...
            if task.source_agent_id:
                result_channel = f"task_results_{task.source_agent_id}"
                await self._message_bus.publish(result_channel, result)
            else:
                print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id for editable check failure.")
            return

        print(f"[{self.agent_id}] Processing task ID: {task.task_id} for code generation.")

        generated_code = None
        error_message_for_generation = None
        status = "completed"
        result_data_content = {"original_request_description": task.description}

        if task.task_type == "code_generation_python_hello_world" or            ("hello world function in python" in task.description.lower()) or            ("hello novapilot" in task.description.lower()):
            generated_code = "def greet():\n    print(\"Hello, NovaPilot!\")\n\ngreet()"
        elif task.task_type == "code_generation_python_sum" or              ("sum function" in task.description.lower()):
            generated_code = "def sum_two_numbers(a, b):\n    return a + b\n"
        elif task.task_type == "code_generation_python": # General python code generation
            generated_code = f"# Code for: {task.description}\npass # Placeholder for general Python code"
        else:
            status = "failed"
            error_message_for_generation = f"Unsupported code generation request. Task description: '{task.description}', Task type: '{task.task_type}' did not match any known patterns."
            print(f"[{self.agent_id}] Task {task.task_id} failed generation: {error_message_for_generation}")

        output_summary = ""
        if status == "completed" and generated_code:
            result_data_content["generated_code_string"] = generated_code
            output_summary = f"Successfully generated code for: {task.description}"

            if target_file_path: # Attempt to write if path provided and editable check passed
                resolved_target_file_path = target_file_path
                project_ctx = await self._get_project_context()
                if project_ctx and project_ctx.root_path and not os.path.isabs(target_file_path):
                    resolved_target_file_path = os.path.join(project_ctx.root_path, target_file_path)

                result_data_content["output_file_path"] = resolved_target_file_path
                try:
                    # Ensure directory exists
                    dir_name = os.path.dirname(resolved_target_file_path)
                    if dir_name: # Check if dirname is not empty (e.g. for files in CWD)
                        os.makedirs(dir_name, exist_ok=True)

                    with open(resolved_target_file_path, "w", encoding="utf-8") as f:
                        f.write(generated_code)
                    result_data_content["file_write_status"] = "success"
                    output_summary += f". Code written to '{resolved_target_file_path}'."
                    print(f"[{self.agent_id}] Code successfully written to '{resolved_target_file_path}'.")
                except (IOError, OSError) as e:
                    write_error = f"Failed to write generated code to '{resolved_target_file_path}': {e}"
                    print(f"[{self.agent_id}] {write_error}")
                    result_data_content["file_write_status"] = write_error
                    # Decide if this makes the overall task "failed" or just part of the output.
                    # For now, let's consider it a partial success if code was generated but write failed.
                    # status = "completed_with_errors" # Or keep "completed" and let user see write_status
                    output_summary += f". Write Error: {write_error}"


        elif status == "failed":
            output_summary = error_message_for_generation if error_message_for_generation else "Code generation failed."

        if target_file_path and "target_file_path" not in result_data_content: # Ensure it's in data if provided in task
             result_data_content["target_file_path"] = target_file_path


        result = ExecutionResult(
            task_id=task.task_id,
            status=status, # Could be "completed_with_errors" if we want to differentiate
            output=output_summary,
            error_message=error_message_for_generation if status == "failed" else None, # Only gen errors here
            data=result_data_content
        )

        if task.source_agent_id:
            result_channel = f"task_results_{task.source_agent_id}"
            await self._message_bus.publish(result_channel, result)
            print(f"[{self.agent_id}] Published generation result for task {task.task_id} to {result_channel}.")
        else:
            print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id for generation result.")

    async def start_listening(self):
        # Agent now listens to its own tasks and discovery requests
        self._listener_tasks.clear()
        self._listener_tasks.append(asyncio.create_task(self._task_listener_loop()))
        self._listener_tasks.append(asyncio.create_task(self._discovery_listener_loop()))
        print(f"[{self.agent_id}] All listeners started.") # Standardized print

    async def _task_listener_loop(self): # Added standard loop
        channel_name = "code_generation_tasks" # Specific channel
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

    async def _discovery_listener_loop(self): # Added standard loop
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
                elif message == f"stop_listening_{channel_name}": # Standardized stop message
                    print(f"[{self.agent_id}] Stop signal received for '{channel_name}' listener.")
                    break
                if self._discovery_queue: self._discovery_queue.task_done()
        except asyncio.CancelledError:
            print(f"[{self.agent_id}] Discovery listener for '{channel_name}' cancelled.")
        finally:
            if self._discovery_queue: await self._message_bus.unsubscribe(channel_name, self._discovery_queue)
            print(f"[{self.agent_id}] Unsubscribed and stopped listening on '{channel_name}'.")

    async def stop_listening(self):
        print(f"[{self.agent_id}] Requesting listeners to stop...")
        task_channel_name = "code_generation_tasks"
        discovery_channel_name = "system_discovery_channel"
        await self._message_bus.publish(task_channel_name, f"stop_listening_{task_channel_name}")
        await self._message_bus.publish(discovery_channel_name, f"stop_listening_{discovery_channel_name}")
        if self._listener_tasks: # Check if list has tasks
            await asyncio.gather(*self._listener_tasks, return_exceptions=True)
        print(f"[{self.agent_id}] All listeners stopped and tasks gathered.") # Standardized print


    # --- ACI Implementation (Stubs - can be filled later if needed) ---
    async def send_message(self, target_agent_id: str, message_content: Any, message_type: str = "generic") -> bool:
        print(f"[{self.agent_id}] send_message to {target_agent_id} called (stub). Content: {message_content}") # Standardized print
        return True

    async def receive_message(self) -> Optional[Any]:
        print(f"[{self.agent_id}] receive_message called (stub).") # Standardized print
        return None

    async def post_task(self, task: Task) -> bool:
        print(f"[{self.agent_id}] post_task called (stub). Task: {task.task_id}") # Standardized print
        return False

    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[ExecutionResult]:
        print(f"[{self.agent_id}] get_task_result for {task_id} called (stub).") # Standardized print
        return None

    def register_event_listener(self, event_type: str, callback: Callable[[Any], None]) -> bool:
        print(f"[{self.agent_id}] register_event_listener for {event_type} called (stub).") # Standardized print
        return True

    async def emit_event(self, event_type: str, event_data: Any) -> bool:
        print(f"[{self.agent_id}] emit_event {event_type} called (stub). Data: {event_data}") # Standardized print
        return True

    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                capability_id="generate_python_code_general",
                task_type="code_generation_python",
                description="Generates Python code snippets. Can write to a file if target_file_path is provided.", # Updated description
                keywords=["generate", "code", "python", "script", "function", "class", "write", "file"], # Added "file"
                required_input_keys=["description"],
                generates_output_keys=["generated_code_string", "output_file_path", "file_write_status"] # Added new keys
            ),
            AgentCapability(
                capability_id="generate_python_hello_world",
                task_type="code_generation_python_hello_world",
                description="Generates a 'Hello, NovaPilot!' Python function. Can write to file.", # Updated
                keywords=["hello", "world", "greet", "print", "simple", "file"], # Added "file"
                required_input_keys=[],
                generates_output_keys=["generated_code_string", "output_file_path", "file_write_status"] # Added
            ),
            AgentCapability(
                capability_id="generate_python_sum_function",
                task_type="code_generation_python_sum",
                description="Generates a Python function to sum two numbers. Can write to file.", # Updated
                keywords=["sum", "add", "numbers", "calculator", "math", "file"], # Added "file"
                required_input_keys=[],
                generates_output_keys=["generated_code_string", "output_file_path", "file_write_status"] # Added
            )
        ]
