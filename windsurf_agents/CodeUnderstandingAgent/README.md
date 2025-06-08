# CodeUnderstandingAgent

The `CodeUnderstandingAgent` is responsible for analyzing and understanding source code.
Its capabilities will include tasks like reading file contents, identifying code structures, dependencies, etc.

## Current Implementation:

-   The agent's logic resides in `code_analyzer.py`.
-   It subscribes to tasks on the `"code_understanding_tasks"` channel of the message bus.
-   Initial functionality will focus on basic file reading and analysis.
