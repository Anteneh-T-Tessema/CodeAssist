# run_example_interaction.py
import asyncio
import os
from novapilot_agents.UserInteractionOrchestratorAgent import UserInteractionOrchestratorAgent
from novapilot_agents.CodeGenerationAgent import CodeGenerationAgent
from novapilot_agents.CodeUnderstandingAgent import CodeUnderstandingAgent
from novapilot_agents.CodeCompletionAgent import CodeCompletionAgent
from novapilot_agents.DebuggingAgent import DebuggingAgent
from novapilot_agents.AutomatedTestingAgent import AutomatedTestingAgent
from novapilot_agents.RefactoringAgent import RefactoringAgent
from novapilot_agents.DocumentationAgent import DocumentationAgent
from novapilot_agents.VersionControlAgent import VersionControlAgent

SAMPLE_FILE_NAME = "sample_code.py"
SAMPLE_TEST_FILE_NAME = "sample_code_test.py"

async def create_sample_files(): # Renamed for clarity, or modify existing
    # Create sample_code.py (existing logic)
    if not os.path.exists(SAMPLE_FILE_NAME):
        print(f"[Setup] Creating sample file: {SAMPLE_FILE_NAME}")
        with open(SAMPLE_FILE_NAME, "w", encoding="utf-8") as f:
            f.write("def hello_sample():\n")
            f.write("    print(\"Hello from sample_code.py!\")\n")
            f.write("\n")
            f.write("# This is a comment\n")
            f.write("# And another one.\n")
            f.write("\n")
            f.write("class SampleClass:\n")
            f.write("    pass\n")
    else:
        print(f"[Setup] Sample file {SAMPLE_FILE_NAME} already exists.")

    # Create sample_code_test.py
    if not os.path.exists(SAMPLE_TEST_FILE_NAME):
        print(f"[Setup] Creating sample test file: {SAMPLE_TEST_FILE_NAME}")
        with open(SAMPLE_TEST_FILE_NAME, "w", encoding="utf-8") as f:
            f.write("# A dummy test file for NovaPilot AutomatedTestingAgent\n")
            f.write("def test_example_feature():\n")
            f.write("    assert True\n")
    else:
        print(f"[Setup] Sample test file {SAMPLE_TEST_FILE_NAME} already exists.")

async def main():
    await create_sample_files() # New call

    orchestrator = UserInteractionOrchestratorAgent(agent_id="orchestrator_01")
    generator = CodeGenerationAgent(agent_id="codegen_agent_01")
    analyzer = CodeUnderstandingAgent(agent_id="code_understanding_agent_01")
    completer = CodeCompletionAgent(agent_id="code_completion_agent_01")
    debugger = DebuggingAgent(agent_id="debugging_agent_01")
    tester = AutomatedTestingAgent(agent_id="automated_testing_agent_01")
    refactorer = RefactoringAgent(agent_id="refactoring_agent_01")
    documenter = DocumentationAgent(agent_id="documentation_agent_01")
    vcs_handler = VersionControlAgent(agent_id="version_control_agent_01")

    print("--- Starting Smart Routing Agent Interaction Example ---")

    # Start agents' listening loops
    print("\n--- Starting Agent Listeners ---")
    orchestrator_listener_task = asyncio.create_task(orchestrator.start_listening())
    generator_listener_task = asyncio.create_task(generator.start_listening())
    analyzer_listener_task = asyncio.create_task(analyzer.start_listening())
    completer_listener_task = asyncio.create_task(completer.start_listening())
    debugger_listener_task = asyncio.create_task(debugger.start_listening())
    tester_listener_task = asyncio.create_task(tester.start_listening())
    refactorer_listener_task = asyncio.create_task(refactorer.start_listening())
    documenter_listener_task = asyncio.create_task(documenter.start_listening())
    vcs_handler_listener_task = asyncio.create_task(vcs_handler.start_listening())

    # Crucial: Allow time for agents to subscribe to channels, especially system_discovery_channel
    await asyncio.sleep(0.5)

    # --- Agent Discovery ---
    print("\n--- Orchestrator Discovering Agents ---")
    await orchestrator.discover_agents()
    # discover_agents has its own sleep, so orchestrator should have the registry populated.
    print(f"[Main] Orchestrator's capability registry: {orchestrator._agent_capabilities_registry}")


    # --- Test User Requests for Smart Routing ---
    print("\n--- Simulating User Requests for Smart Routing ---")

    # Request that should route to CodeGenerationAgent (hello world)
    task_id_cg1 = await orchestrator.receive_user_request(
        request_text="Please create a python script for a hello world greet function"
    )
    if task_id_cg1:
        print(f"[Main] Orchestrator accepted request (expected CG Agent), Task ID: {task_id_cg1}")

    # --- Code Understanding Request ---
    print("\n--- Simulating Code Understanding User Request ---")
    # Request for existing sample file using relative path
    task_id_cu1 = await orchestrator.receive_user_request(
        request_text=f"analyze file {SAMPLE_FILE_NAME}" # SAMPLE_FILE_NAME is "sample_code.py"
    )
    if task_id_cu1:
        print(f"[Main] Orchestrator accepted analysis request for '{SAMPLE_FILE_NAME}', Task ID: {task_id_cu1}")

    # Request that should route to CodeGenerationAgent (sum function)
    task_id_cg2 = await orchestrator.receive_user_request(
        request_text="I need to write code to sum numbers"
    )
    if task_id_cg2:
        print(f"[Main] Orchestrator accepted request (expected CG Agent), Task ID: {task_id_cg2}")

    # Request for a non-existent file using relative path
    task_id_cu2 = await orchestrator.receive_user_request(
        request_text="analyze file non_existent_relative.py" # Using a new name for clarity
    )
    if task_id_cu2:
        print(f"[Main] Orchestrator accepted analysis request for 'non_existent_relative.py' (expected fail), Task ID: {task_id_cu2}")

    # Request that should be unroutable
    task_id_unroutable = await orchestrator.receive_user_request(
        request_text="Tell me a joke"
    )
    if task_id_unroutable: # Will still get a task_id, but task status should be 'unroutable'
        print(f"[Main] Orchestrator accepted request (expected Unroutable), Task ID: {task_id_unroutable}")

    # --- Test Input Validation Failure ---
    print("\n--- Simulating User Request for Input Validation Failure ---")
    # This request should match CodeUnderstandingAgent's capability by keywords,
    # but will fail validation because "file_path" is missing and cannot be easily extracted.
    task_id_invalid_input = await orchestrator.receive_user_request(
        request_text="analyze the lines of my text", # No filename-like string
        task_data={} # Explicitly empty task_data
    )
    if task_id_invalid_input:
        print(f"[Main] Orchestrator accepted request (expected Input Validation Fail), Task ID: {task_id_invalid_input}")

    # --- Test File Editable Check in CodeGenerationAgent ---
    print("\n--- Simulating User Requests for Editable File Check ---")

    # Test case 1: Target file is NOT editable
    task_id_cg_non_editable = await orchestrator.receive_user_request(
        request_text="generate python sum function and save to temp/test_non_editable.py"
        # Orchestrator's test hook should set target_file_is_editable = False for this path
    )
    if task_id_cg_non_editable:
        print(f"[Main] Orchestrator accepted request (expected CG Agent to fail on non-editable), Task ID: {task_id_cg_non_editable}")

    # Test case 2: Target file IS editable
    task_id_cg_editable = await orchestrator.receive_user_request(
        request_text="generate python hello world and save to temp/test_editable.py"
        # Orchestrator's test hook should set target_file_is_editable = True for this path
    )
    if task_id_cg_editable:
        print(f"[Main] Orchestrator accepted request (expected CG Agent to proceed), Task ID: {task_id_cg_editable}")

    # --- Test CodeCompletionAgent ---
    print("\n--- Simulating User Request for Code Completion ---")
    task_id_completion1 = await orchestrator.receive_user_request(
        request_text="complete python def"
        # Orchestrator's test hook should populate task.data for this.
    )
    if task_id_completion1:
        print(f"[Main] Orchestrator accepted request (expected CodeCompletionAgent), Task ID: {task_id_completion1}")

    # --- Test DebuggingAgent ---
    print("\n--- Simulating User Requests for Debugging Agent ---")

    # Test case 1: Debug existing file
    task_id_debug1 = await orchestrator.receive_user_request(
        request_text=f"debug file {SAMPLE_FILE_NAME}"
        # Orchestrator's test hook should populate task.data.
        # SAMPLE_FILE_NAME is "sample_code.py" which should exist.
    )
    if task_id_debug1:
        print(f"[Main] Orchestrator accepted request (expected DebuggingAgent, file exists), Task ID: {task_id_debug1}")

    # Test case 2: Debug non-existent file
    DEBUG_NON_EXISTENT_FILE = "non_existent_debug_target.py"
    task_id_debug2 = await orchestrator.receive_user_request(
        request_text=f"debug file {DEBUG_NON_EXISTENT_FILE}"
        # Orchestrator's test hook should populate task.data.
    )
    if task_id_debug2:
        print(f"[Main] Orchestrator accepted request (expected DebuggingAgent, file not found), Task ID: {task_id_debug2}")

    # --- Test AutomatedTestingAgent ---
    print("\n--- Simulating User Requests for Automated Testing Agent ---")

    # Test case 1: Run tests for a recognized _test.py file
    task_id_test1 = await orchestrator.receive_user_request(
        request_text=f"run tests for {SAMPLE_TEST_FILE_NAME}"
    )
    if task_id_test1:
        print(f"[Main] Orchestrator accepted request (expected AT Agent, recognized test file), Task ID: {task_id_test1}")

    # Test case 2: Run tests for a non-test file
    task_id_test2 = await orchestrator.receive_user_request(
        request_text=f"run tests for {SAMPLE_FILE_NAME}"
    )
    if task_id_test2:
        print(f"[Main] Orchestrator accepted request (expected AT Agent, not a test file), Task ID: {task_id_test2}")

    # Test case 3: Run tests with missing file path (should fail at agent or orchestrator validation if strict)
    task_id_test3 = await orchestrator.receive_user_request(
        request_text="run tests"
    )
    if task_id_test3:
        print(f"[Main] Orchestrator accepted request (expected AT Agent, missing path), Task ID: {task_id_test3}")


    print("\n--- Allowing time for task processing (approx 4 seconds) ---")
    await asyncio.sleep(4)

    print("\n--- Checking Task Statuses in Orchestrator ---")
    tasks_to_check = [
        task_id_cg1, task_id_cu1, task_id_cg2, task_id_cu2,
        task_id_unroutable, task_id_invalid_input,
        task_id_cg_non_editable, task_id_cg_editable,
        task_id_completion1,
        task_id_debug1, task_id_debug2,
        task_id_test1, task_id_test2, task_id_test3 # Added here
    ]
    for task_id in tasks_to_check:
        if task_id and task_id in orchestrator._active_tasks:
            task_info = orchestrator._active_tasks[task_id]
            print(f"[Main] Task ID: {task_id}, Type: '{task_info.task_type}', Target: '{task_info.target_agent_id}', Status: '{task_info.status}', Desc: '{task_info.description}'")
            # Note: The actual ExecutionResult.data is logged by the orchestrator's _listen_for_results.
            # Accessing it here would require the orchestrator to store it on the task_info or a separate registry.
            # For now, we rely on the orchestrator's log for result.data details.


    print("\n--- Sending Stop Signals to Agents ---")
    # Important: Stop orchestrator's main listeners first if they might try to process things
    # while other agents are shutting down their discovery listeners.
    # However, the discovery responses listener of orchestrator should be robust.
    await orchestrator.stop_listening()
    await generator.stop_listening()
    await analyzer.stop_listening()
    await completer.stop_listening()
    await debugger.stop_listening()
    await tester.stop_listening()
    await refactorer.stop_listening()
    await documenter.stop_listening()
    await vcs_handler.stop_listening()

    print("\n--- Waiting for Agent Listeners to Finish ---")
    # Gather all main listener tasks
    all_listener_tasks = [orchestrator_listener_task]
    # The agent's stop_listening methods should internally await their own specific listener tasks (like task loop and discovery loop)
    # So we only need to gather the main tasks returned by asyncio.create_task for each agent's start_listening here.
    # The individual agent's stop_listening() should handle the gathering of its own internal tasks.
    if hasattr(generator, '_listener_tasks'): # If generator stored its listener tasks for its stop_listening
        all_listener_tasks.extend(generator._listener_tasks) # This is incorrect, generator.stop_listening already gathers them
    if hasattr(analyzer, '_listener_tasks'): # Same for analyzer
        all_listener_tasks.extend(analyzer._listener_tasks)   # This is incorrect

    # Correct approach: The start_listening method should return the main listener task(s)
    # or be designed such that stop_listening handles all cleanup.
    # Our current agent's start_listening() launches tasks but doesn't make them easily awaitable from outside
    # other than via their own stop_listening().

    # The `stop_listening` methods in agents now internally gather their own listener tasks.
    # So, we only need to await the main orchestrator listener task here,
    # as the agent specific `stop_listening` calls are awaited.
    # However, the initial `asyncio.create_task` for agent listeners should also be awaited or gathered.

    await asyncio.gather(
        orchestrator_listener_task,
        generator_listener_task,
        analyzer_listener_task,
        completer_listener_task,
        debugger_listener_task,
        tester_listener_task,
        refactorer_listener_task,   # New
        documenter_listener_task, # New
        vcs_handler_listener_task,  # New
        return_exceptions=True
    )

    print("\n--- Smart Routing Agent Interaction Example Finished ---")

if __name__ == "__main__":
    asyncio.run(main())
