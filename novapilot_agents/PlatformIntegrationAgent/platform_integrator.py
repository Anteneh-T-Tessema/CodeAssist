# novapilot_agents/PlatformIntegrationAgent/platform_integrator.py
import asyncio
import uuid
import os
from typing import Optional, Any, Callable, Dict, List

from novapilot_core.aci import AgentCommunicationInterface
from novapilot_core.models import Task, ExecutionResult, AgentCapability, ProjectContext
from novapilot_core.message_bus import message_bus

class PlatformIntegrationAgent(AgentCommunicationInterface):
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

    async def _process_task(self, task: Task):
        print(f"[{self.agent_id}] Received PlatformIntegration task: {task.description}, Type: {task.task_type}, Data: {task.data}")

        # Capability "notify_slack_channel" expects:
        # required_input_keys=["slack_channel_id", "message_text", "notification_type"]

        status = "completed"
        output_message = ""
        result_data_content = {"original_request_description": task.description}

        # project_ctx = await self._get_project_context() # Available if needed for other integrations

        if task.task_type == "platform_integration_slack_notification":
            slack_channel_id = task.data.get("slack_channel_id")
            message_text = task.data.get("message_text")
            notification_type = task.data.get("notification_type", "info") # Default type

            if not all([slack_channel_id, message_text]):
                status = "failed"
                missing = []
                if not slack_channel_id: missing.append("slack_channel_id")
                if not message_text: missing.append("message_text")
                output_message = f"Missing required data for Slack notification: {', '.join(missing)}."
                result_data_content["error"] = output_message
                print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")
            else:
                # Simulate sending Slack message
                output_message = f"Simulated sending message to Slack channel '{slack_channel_id}' (Type: {notification_type}): '{message_text}'."
                result_data_content["notification_id"] = f"sim_slack_{str(uuid.uuid4())[:8]}"
                result_data_content["delivery_status"] = "simulated_sent"
                result_data_content["slack_channel_id"] = slack_channel_id
                result_data_content["message_sent"] = message_text
                print(f"[{self.agent_id}] {output_message}")

        elif task.task_type == "platform_integration_github_pull_request":
            # Placeholder for GitHub PR simulation - for now, just "not implemented" for this task type
            output_message = f"GitHub PR integration for '{task.description}' not implemented in this basic version."
            # Mark as 'completed' because the agent processed the type, but no action for now
            result_data_content["status_message"] = "specific_action_not_implemented"
            print(f"[{self.agent_id}] {output_message}")
            # For a more complete stub, you might check for its required_input_keys here too.
            # For now, this capability's tasks will appear to "succeed" but do nothing.
        else:
            status = "failed"
            output_message = f"Unknown task type '{task.task_type}' for PlatformIntegrationAgent."
            result_data_content["error"] = output_message
            print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")

        if status == "failed" and "error" not in result_data_content : # Ensure error key exists if failed
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
            print(f"[{self.agent_id}] Published platform integration result for task {task.task_id} to {result_channel}.")
        else:
            print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id. Cannot publish result.")

    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                capability_id="integrate_with_github_pr",
                task_type="platform_integration_github_pull_request",
                description="Integrates with GitHub to create or update Pull Requests.",
                keywords=["platform", "integration", "github", "pull request", "pr", "vcs hosting"],
                required_input_keys=["repository_url", "branch_name", "pr_title", "pr_body", "target_branch"],
                generates_output_keys=["pr_url", "pr_status", "integration_log"]
            ),
            AgentCapability(
                capability_id="notify_slack_channel",
                task_type="platform_integration_slack_notification",
                description="Sends a notification message to a specified Slack channel.",
                keywords=["platform", "integration", "slack", "notify", "message", "chatops"],
                required_input_keys=["slack_channel_id", "message_text", "notification_type"],
                generates_output_keys=["notification_id", "delivery_status"]
            )
        ]

    async def _task_listener_loop(self):
        channel_name = "platform_integration_tasks"
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
        task_channel_name = "platform_integration_tasks"
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
