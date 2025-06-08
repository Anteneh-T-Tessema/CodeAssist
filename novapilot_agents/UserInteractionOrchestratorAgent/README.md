# UserInteractionOrchestratorAgent

The `UserInteractionOrchestratorAgent` is responsible for managing the interaction between the user and the NovaPilot agent ecosystem.

## Key Responsibilities:

-   **Receiving User Requests:** Simulates receiving requests from a user via the `receive_user_request(request_text: str, ...)` method.
-   **Task Management:**
    -   Creates unique `Task` objects for user requests.
    -   Tracks active tasks and their statuses (e.g., pending_dispatch, dispatched, completed, failed).
    -   Dispatches tasks to appropriate specialized agents (currently, primarily `CodeGenerationAgent`) using the `post_task(task: Task)` method via the message bus.
-   **Result Handling:**
    -   Listens for `ExecutionResult` objects on a dedicated message bus channel (`task_results_{self.agent_id}`).
    -   Updates the status of tasks based on received results.
-   **Lifecycle Management:** Uses `start_listening()` to begin listening for results and `stop_listening()` for graceful shutdown.

## Current Implementation:

-   The agent's logic resides in `orchestrator.py`.
-   It uses the global `message_bus` from `novapilot_core` for communication.
-   Task routing is currently basic and may be expanded in the future.
