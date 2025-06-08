# run_example_interaction.py
import asyncio
from windsurf_agents.UserInteractionOrchestratorAgent import MockOrchestratorAgent
from windsurf_agents.CodeGenerationAgent import MockCodeGeneratorAgent
from windsurf_core.message_bus import message_bus # For potentially sending a stop signal

async def main():
    orchestrator = MockOrchestratorAgent(agent_id="orchestrator_01")
    generator = MockCodeGeneratorAgent(agent_id="codegen_agent_01")

    print("Starting example interaction...")

    # Start the generator listening for tasks
    generator_listener_task = asyncio.create_task(generator.listen_for_tasks())

    # Give the listener a moment to subscribe
    await asyncio.sleep(0.1)

    # Orchestrator sends a task
    await orchestrator.send_task_to_generator("Create a Python function that prints 'Hello, Windsurf!'")

    # Simulate some time for processing or other tasks
    await asyncio.sleep(2)

    # Send a stop signal to the generator's listener loop
    print("Sending stop signal to generator...")
    await message_bus.publish("code_generation_tasks", "stop_listening")

    # Wait for the generator to finish its current tasks and stop listening
    await generator_listener_task

    print("Example interaction finished.")

if __name__ == "__main__":
    asyncio.run(main())
