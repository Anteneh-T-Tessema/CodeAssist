# run_example_interaction.py
import asyncio
import os
from novapilot_agents.UserInteractionOrchestratorAgent import UserInteractionOrchestratorAgent
from novapilot_agents.CodeGenerationAgent import CodeGenerationAgent
from novapilot_agents.CodeUnderstandingAgent import CodeUnderstandingAgent

SAMPLE_FILE_NAME = "sample_code.py"

async def create_sample_file_if_not_exists():
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

async def main():
    await create_sample_file_if_not_exists()

    orchestrator = UserInteractionOrchestratorAgent(agent_id="orchestrator_01")
    generator = CodeGenerationAgent(agent_id="codegen_agent_01")
    analyzer = CodeUnderstandingAgent(agent_id="code_understanding_agent_01")

    print("--- Starting Smart Routing Agent Interaction Example ---")

    # Start agents' listening loops
    print("\n--- Starting Agent Listeners ---")
    orchestrator_listener_task = asyncio.create_task(orchestrator.start_listening())
    generator_listener_task = asyncio.create_task(generator.start_listening())
    analyzer_listener_task = asyncio.create_task(analyzer.start_listening())

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


    print("\n--- Allowing time for task processing (approx 4 seconds) ---")
    await asyncio.sleep(4)

    print("\n--- Checking Task Statuses in Orchestrator ---")
    tasks_to_check = [task_id_cg1, task_id_cu1, task_id_cg2, task_id_cu2, task_id_unroutable]
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
        orchestrator_listener_task, # This is for orchestrator's _listen_for_results and _listen_for_discovery_responses
        generator_listener_task,    # This is for generator's combined listener setup in its start_listening
        analyzer_listener_task,     # This is for analyzer's combined listener setup in its start_listening
        return_exceptions=True
    )

    print("\n--- Smart Routing Agent Interaction Example Finished ---")

if __name__ == "__main__":
    asyncio.run(main())
