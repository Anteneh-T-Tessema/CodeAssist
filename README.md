# NovaPilot: End-to-End Software Development Agent

This project, NovaPilot, aims to build an advanced AI-powered software development assistant. It is composed of several specialized agents that collaborate to provide a comprehensive development environment.

## Project Structure

The core of the project is organized into the following agent modules, located in the `novapilot_agents` directory:

- **UserInteractionOrchestratorAgent**: Manages communication and task flow between the user and other agents.
- **CodeUnderstandingAgent**: Analyzes and understands existing codebases.
- **CodeGenerationAgent**: Generates new code based on requirements.
- **CodeCompletionAgent**: Provides intelligent code completion suggestions.
- **DebuggingAgent**: Helps identify and fix bugs in code.
- **AutomatedTestingAgent**: Generates and runs automated tests.
- **RefactoringAgent**: Assists in restructuring and improving existing code.
- **DocumentationAgent**: Generates and maintains project documentation.
- **VulnerabilityScanAgent**: Scans code for security vulnerabilities.
- **EnvironmentManagementAgent**: Manages development environments and dependencies.
- **PlatformIntegrationAgent**: Integrates with various development platforms and tools.
- **VersionControlAgent**: Handles version control operations (e.g., Git).
- **KnowledgeBaseAgent**: Manages and retrieves information relevant to the development process.
- **AgentLifecycleManagerAgent**: Manages the lifecycle of the different agents.
- **AgentSandboxAgent**: Provides a sandboxed environment for code execution and testing.

Further details about each agent and their functionalities will be added as development progresses.

## Core Communication Infrastructure (`novapilot_core`)

To facilitate communication and data exchange between the various agents, a dedicated `novapilot_core` package has been established. This package contains the foundational elements for inter-agent interaction:

-   **`novapilot_core/models.py`**: Defines the core data structures (Python dataclasses) used for communication. This includes `Task`, `FileContext`, `CodeBlock`, `ExecutionResult`, and `UserFeedback`, ensuring a standardized format for information passed between agents.

-   **`novapilot_core/aci.py`**: (Agent Communication Interface) Contains the `AgentCommunicationInterface`, an abstract base class (ABC) that defines the standard methods and properties agents must implement for communication. This promotes consistency in how agents send/receive messages, handle tasks, and manage events.

-   **`novapilot_core/message_bus.py`**: Implements a simple, in-memory `MessageBus`. This allows agents to communicate asynchronously using a publish-subscribe pattern. Agents can publish messages to specific channels (topics), and other agents can subscribe to these channels to receive relevant information, promoting loose coupling. A global instance `message_bus` is provided for ease of use in the current development phase.

These core components are essential for enabling coordinated and effective collaboration among the specialized agents within the NovaPilot ecosystem.