# novapilot_agents/KnowledgeBaseAgent/kb_manager.py
import asyncio
import uuid
import os
from typing import Optional, Any, Callable, Dict, List

from novapilot_core.aci import AgentCommunicationInterface
from novapilot_core.models import Task, ExecutionResult, AgentCapability, ProjectContext
from novapilot_core.message_bus import message_bus

class KnowledgeBaseAgent(AgentCommunicationInterface):
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
        print(f"[{self.agent_id}] Received KnowledgeBase task: {task.description}, Type: {task.task_type}, Data: {task.data}")

        status = "completed"
        output_message = ""
        result_data_content = {"original_request_description": task.description}

        if task.task_type == "kb_query":
            query_string = task.data.get("query_string")
            # filters = task.data.get("filters") # Not used in this simulation

            if not query_string:
                status = "failed"
                output_message = "Missing 'query_string' in task data for kb_query."
                result_data_content["error"] = output_message
                print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")
            else:
                # Simulate KB query
                await asyncio.sleep(0.1) # Simulate query time
                query_lower = query_string.lower()
                results_list = []

                if "hello" in query_lower or "novapilot" in query_lower:
                    results_list.append({
                        "document_id": "doc_sim_001",
                        "content_snippet": "NovaPilot is an advanced AI-powered software development assistant (simulated).",
                        "relevance_score": 0.95,
                        "source_document": "internal_docs/novapilot_overview.md"
                    })
                    if "architecture" in query_lower: # Add another dummy result for more specific query
                         results_list.append({
                            "document_id": "doc_sim_002",
                            "content_snippet": "NovaPilot uses a microservices architecture with a central orchestrator (simulated).",
                            "relevance_score": 0.88,
                            "source_document": "internal_docs/architecture_deep_dive.md"
                        })
                    output_message = f"Found {len(results_list)} simulated document(s) for query: '{query_string}'."
                    print(f"[{self.agent_id}] {output_message}")
                else:
                    output_message = f"No simulated documents found for query: '{query_string}'."
                    print(f"[{self.agent_id}] {output_message}")

                result_data_content["query_results_list"] = results_list
                result_data_content["relevance_scores"] = [res["relevance_score"] for res in results_list] # Example
                result_data_content["source_documents"] = [res["source_document"] for res in results_list] # Example
                result_data_content["query_string_processed"] = query_string

        elif task.task_type == "kb_store":
            # For now, just acknowledge and say not implemented for actual storage
            status = "not_implemented" # Explicitly not_implemented
            output_message = f"Storage operation for document_id '{task.data.get('document_id', 'N/A')}' not implemented yet."
            result_data_content["status_message"] = "not_implemented"
            result_data_content["storage_confirmation_id"] = None
            result_data_content["indexing_status"] = "pending_implementation"
            print(f"[{self.agent_id}] {output_message}")

        else:
            status = "failed" # Or "not_implemented" if we want to be more specific for unknown task types
            output_message = f"Unknown task type '{task.task_type}' for KnowledgeBaseAgent."
            result_data_content["error"] = output_message
            print(f"[{self.agent_id}] Task {task.task_id} failed: {output_message}")

        if status == "failed" and "error" not in result_data_content:
            result_data_content["error"] = output_message

        result = ExecutionResult(
            task_id=task.task_id,
            status=status,
            output=output_message,
            data=result_data_content,
            error_message=output_message if status in ["failed", "not_implemented"] else None
            # error_message if truly an error, or if not_implemented is also an error condition for caller
        )

        if task.source_agent_id:
            result_channel = f"task_results_{task.source_agent_id}"
            await self._message_bus.publish(result_channel, result)
            print(f"[{self.agent_id}] Published KnowledgeBase result for task {task.task_id} to {result_channel}.")
        else:
            print(f"[{self.agent_id}] Warning: Task {task.task_id} has no source_agent_id. Cannot publish result.")

    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                capability_id="kb_query_information",
                task_type="kb_query",
                description="Queries the knowledge base for information related to a given topic or keywords.",
                keywords=["kb", "knowledge base", "query", "search", "find", "information", "documentation", "faq"],
                required_input_keys=["query_string", "filters"], # Example keys
                generates_output_keys=["query_results_list", "relevance_scores", "source_documents"] # Example keys
            ),
            AgentCapability(
                capability_id="kb_store_information",
                task_type="kb_store",
                description="Stores or updates information in the knowledge base.",
                keywords=["kb", "knowledge base", "store", "add", "update", "index", "information"],
                required_input_keys=["document_content", "document_id", "metadata_tags"], # Example keys
                generates_output_keys=["storage_confirmation_id", "indexing_status"] # Example keys
            )
        ]

    async def _task_listener_loop(self):
        channel_name = "knowledge_base_tasks"
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
        task_channel_name = "knowledge_base_tasks"
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
