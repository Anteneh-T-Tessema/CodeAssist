# run_example_interaction.py
import asyncio
from windsurf_agents.UserInteractionOrchestratorAgent import UserInteractionOrchestratorAgent
from windsurf_agents.CodeGenerationAgent import CodeGenerationAgent
# message_bus is not directly used here for sending stop signals to individual agents anymore,
# as agents now have their own stop_listening methods which handle publishing the stop signal.

async def main():
    orchestrator = UserInteractionOrchestratorAgent(agent_id="orchestrator_01")
    generator = CodeGenerationAgent(agent_id="codegen_agent_01")

    print("--- Starting Enhanced Agent Interaction Example ---")

    # Start agents' listening loops
    # These tasks will run in the background
    orchestrator_listener_task = asyncio.create_task(orchestrator.start_listening())
    generator_listener_task = asyncio.create_task(generator.start_listening())

    # Give listeners a moment to subscribe
    await asyncio.sleep(0.2) # Increased slightly to ensure subscriptions are processed

    # Simulate a user request to the orchestrator
    print("\n--- Simulating User Request ---")
    task_id_1 = await orchestrator.receive_user_request(
        request_text="Create a Python function that prints 'Hello, Windsurf!'",
        target_agent_id="codegen_agent_01"
    )
    if task_id_1:
        print(f"[Main] Orchestrator accepted user request, Task ID: {task_id_1}")

    # Simulate another user request for a different function
    await asyncio.sleep(0.1) # Small delay between requests
    task_id_2 = await orchestrator.receive_user_request(
        request_text="Create a sum function",
        target_agent_id="codegen_agent_01",
        task_data={"details": "Generate a Python function that sums two numbers."}
    )
    if task_id_2:
        print(f"[Main] Orchestrator accepted user request, Task ID: {task_id_2}")

    # Simulate a user request that should fail
    await asyncio.sleep(0.1)
    task_id_3 = await orchestrator.receive_user_request(
        request_text="Bake a cake", # This should be handled as a failed task by the generator
        target_agent_id="codegen_agent_01"
    )
    if task_id_3:
        print(f"[Main] Orchestrator accepted user request, Task ID: {task_id_3}")


    # Allow time for tasks to be processed and results to be received
    print("\n--- Allowing time for task processing (approx 3 seconds) ---")
    await asyncio.sleep(3) # Adjust as needed based on agent processing times

    # Check status of tasks in orchestrator (optional demonstration)
    print("\n--- Checking Task Statuses in Orchestrator ---")
    if task_id_1 and task_id_1 in orchestrator._active_tasks:
        print(f"[Main] Status of Task {task_id_1}: {orchestrator._active_tasks[task_id_1].status}")
    if task_id_2 and task_id_2 in orchestrator._active_tasks:
        print(f"[Main] Status of Task {task_id_2}: {orchestrator._active_tasks[task_id_2].status}")
    if task_id_3 and task_id_3 in orchestrator._active_tasks:
        print(f"[Main] Status of Task {task_id_3}: {orchestrator._active_tasks[task_id_3].status}")


    # Gracefully stop agents' listening loops
    print("\n--- Sending Stop Signals to Agents ---")
    await orchestrator.stop_listening()
    await generator.stop_listening()

    # Wait for listener tasks to complete
    print("\n--- Waiting for Agent Listeners to Finish ---")
    await asyncio.gather(orchestrator_listener_task, generator_listener_task, return_exceptions=True)

    print("\n--- Enhanced Agent Interaction Example Finished ---")

if __name__ == "__main__":
    asyncio.run(main())
