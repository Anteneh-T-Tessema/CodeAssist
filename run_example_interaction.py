# run_example_interaction.py
import asyncio
import os # For creating a dummy file path if needed
from windsurf_agents.UserInteractionOrchestratorAgent import UserInteractionOrchestratorAgent
from windsurf_agents.CodeGenerationAgent import CodeGenerationAgent
from windsurf_agents.CodeUnderstandingAgent import CodeUnderstandingAgent # Import new agent

# Define the sample file name globally or pass it around
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
    analyzer = CodeUnderstandingAgent(agent_id="code_understanding_agent_01") # Instantiate

    print("--- Starting Full Agent Interaction Example ---")

    # Start agents' listening loops
    orchestrator_listener_task = asyncio.create_task(orchestrator.start_listening())
    generator_listener_task = asyncio.create_task(generator.start_listening())
    analyzer_listener_task = asyncio.create_task(analyzer.start_listening()) # Start listener

    await asyncio.sleep(0.3) # Allow all listeners to subscribe

    # --- Code Generation Requests ---
    print("\n--- Simulating Code Generation User Requests ---")
    task_id_gen_1 = await orchestrator.receive_user_request(
        request_text="Create a Python function that prints 'Hello, Windsurf!'",
        target_agent_id="codegen_agent_01"
    )
    if task_id_gen_1:
        print(f"[Main] Orchestrator accepted codegen request, Task ID: {task_id_gen_1}")

    task_id_gen_2 = await orchestrator.receive_user_request(
        request_text="Bake a cake", # This should fail at the generator
        target_agent_id="codegen_agent_01"
    )
    if task_id_gen_2:
        print(f"[Main] Orchestrator accepted codegen request (expected fail), Task ID: {task_id_gen_2}")

    # --- Code Understanding Request ---
    print("\n--- Simulating Code Understanding User Request ---")
    task_id_analyze_1 = await orchestrator.receive_user_request(
        request_text=f"analyze file {SAMPLE_FILE_NAME}"
        # Target agent will be determined by orchestrator's logic
    )
    if task_id_analyze_1:
        print(f"[Main] Orchestrator accepted analysis request, Task ID: {task_id_analyze_1}")

    # Simulate a file not found scenario
    task_id_analyze_2 = await orchestrator.receive_user_request(
        request_text="analyze file non_existent_file.py"
    )
    if task_id_analyze_2:
        print(f"[Main] Orchestrator accepted analysis request (expected fail), Task ID: {task_id_analyze_2}")


    print("\n--- Allowing time for task processing (approx 4 seconds) ---")
    await asyncio.sleep(4)

    print("\n--- Checking Task Statuses in Orchestrator ---")
    tasks_to_check = [task_id_gen_1, task_id_gen_2, task_id_analyze_1, task_id_analyze_2]
    for task_id in tasks_to_check:
        if task_id and task_id in orchestrator._active_tasks:
            task_info = orchestrator._active_tasks[task_id]
            print(f"[Main] Status of Task {task_id} ({task_info.description}): {task_info.status}")
            # Try to get final result details if available (and status implies result is processed)
            if task_info.status in ["completed", "failed"]:
                # The result itself isn't directly stored on the task object by default in the current orchestrator.
                # The orchestrator prints results when they arrive in _listen_for_results.
                # For more detailed result checking here, orchestrator would need to store them.
                pass


    print("\n--- Sending Stop Signals to Agents ---")
    await orchestrator.stop_listening()
    await generator.stop_listening()
    await analyzer.stop_listening() # Stop analyzer

    print("\n--- Waiting for Agent Listeners to Finish ---")
    await asyncio.gather(
        orchestrator_listener_task,
        generator_listener_task,
        analyzer_listener_task, # Gather analyzer task
        return_exceptions=True
    )

    print("\n--- Full Agent Interaction Example Finished ---")

if __name__ == "__main__":
    # The sample file is created at the start of main()
    asyncio.run(main())
