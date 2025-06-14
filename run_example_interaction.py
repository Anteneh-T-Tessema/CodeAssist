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
from novapilot_agents.VulnerabilityScanAgent import VulnerabilityScanAgent
from novapilot_agents.EnvironmentManagementAgent import EnvironmentManagementAgent
from novapilot_agents.PlatformIntegrationAgent import PlatformIntegrationAgent
from novapilot_agents.KnowledgeBaseAgent import KnowledgeBaseAgent
from novapilot_agents.AgentLifecycleManagerAgent import AgentLifecycleManagerAgent
from novapilot_agents.AgentSandboxAgent import AgentSandboxAgent
from novapilot_agents.GuardrailAgent import GuardrailAgent
from novapilot_agents.EvaluationAgent import EvaluationAgent

SAMPLE_FILE_NAME = "sample_code.py"
SAMPLE_TEST_FILE_NAME = "sample_code_test.py"
SAMPLE_FUNCTION_NAME = "hello_sample" # For DocumentationAgent tests

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
    vuln_scanner = VulnerabilityScanAgent(agent_id="vulnerability_scan_agent_01")
    env_manager = EnvironmentManagementAgent(agent_id="environment_management_agent_01")
    platform_integrator = PlatformIntegrationAgent(agent_id="platform_integration_agent_01")
    kb_manager = KnowledgeBaseAgent(agent_id="knowledge_base_agent_01")
    lifecycle_mgr = AgentLifecycleManagerAgent(agent_id="agent_lifecycle_manager_agent_01")
    sandbox_mgr = AgentSandboxAgent(agent_id="agent_sandbox_agent_01")
    guardrail_checker = GuardrailAgent(agent_id="guardrail_agent_01")
    evaluator = EvaluationAgent(agent_id="evaluation_agent_01")

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
    vuln_scanner_listener_task = asyncio.create_task(vuln_scanner.start_listening())
    env_manager_listener_task = asyncio.create_task(env_manager.start_listening())
    platform_integrator_listener_task = asyncio.create_task(platform_integrator.start_listening())
    kb_manager_listener_task = asyncio.create_task(kb_manager.start_listening())
    lifecycle_mgr_listener_task = asyncio.create_task(lifecycle_mgr.start_listening())
    sandbox_mgr_listener_task = asyncio.create_task(sandbox_mgr.start_listening())
    guardrail_listener_task = asyncio.create_task(guardrail_checker.start_listening())
    evaluator_listener_task = asyncio.create_task(evaluator.start_listening())

    # Crucial: Allow time for agents to subscribe to channels, especially system_discovery_channel
    await asyncio.sleep(0.5)

    # --- Agent Discovery ---
    print("\n--- Orchestrator Discovering Agents ---")
    await orchestrator.discover_agents()
    # discover_agents has its own sleep, so orchestrator should have the registry populated.
    print(f"[Main] Orchestrator's capability registry: {orchestrator._agent_capabilities_registry}")

    # Add this block for verifying ProjectContext loading:
    print("\n--- Orchestrator's Project Context ---")
    if orchestrator._project_context:
        print(f"[Main] Project ID: {orchestrator._project_context.project_id}")
        print(f"[Main] Project Name: {orchestrator._project_context.project_name}")
        print(f"[Main] Root Path: {orchestrator._project_context.root_path}")
        print(f"[Main] Main Language: {orchestrator._project_context.main_language}")
        print(f"[Main] VCS Type: {orchestrator._project_context.vcs_type}")
        print(f"[Main] VCS Branch: {orchestrator._project_context.vcs_branch}")
        print(f"[Main] Metadata: {orchestrator._project_context.metadata}")
    else:
        print("[Main] Orchestrator's ProjectContext is None.")

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

    # --- Test CodeGenerationAgent File Writing ---
    print("\n--- Simulating User Requests for Code Generation Agent File Writing ---")

    # Test case 1 (existing, now with file write implication): Target file is NOT editable
    # Request: "generate python sum function and save to temp/test_non_editable.py"
    # Orchestrator hook sets target_file_is_editable = False
    # Expected: Agent's editable pre-check fails, no file written. Status: failed.
    task_id_cg_non_editable_write = await orchestrator.receive_user_request(
        request_text="generate python sum function and save to temp/test_non_editable.py"
    )
    if task_id_cg_non_editable_write:
        print(f"[Main] Orchestrator accepted CG request (non-editable file write), Task ID: {task_id_cg_non_editable_write}")

    # Test case 2 (existing, now with file write implication): Target file IS editable (but might be a specific test path)
    # Request: "generate python hello world and save to temp/test_editable.py"
    # Orchestrator hook sets target_file_is_editable = True
    # Expected: Agent's editable pre-check passes. File "temp/test_editable.py" is written with hello world code. Status: completed.
    task_id_cg_editable_write = await orchestrator.receive_user_request(
        request_text="generate python hello world and save to temp/test_editable.py"
    )
    if task_id_cg_editable_write:
        print(f"[Main] Orchestrator accepted CG request (editable file write to temp), Task ID: {task_id_cg_editable_write}")

    # Test case 3: Generate code and save to a new file in a new directory
    NEW_SCRIPT_PATH = "generated_code/cg_new_script.py"
    task_id_cg_new_file = await orchestrator.receive_user_request(
        request_text=f"generate python code for a simple class MyClass with an init method and save to {NEW_SCRIPT_PATH}"
        # Orchestrator general "save to" hook will set target_file_path and default target_file_is_editable=True
    )
    if task_id_cg_new_file:
        print(f"[Main] Orchestrator accepted CG request (new file write), Task ID: {task_id_cg_new_file}")

    # Test case 4: Generate code, save to existing file (e.g., sample_code.py), expecting overwrite
    # For this, we need to ensure the orchestrator hook handles this without a specific "temp/" path.
    # The general " save to " hook should work.
    task_id_cg_overwrite_sample = await orchestrator.receive_user_request(
        request_text=f"generate python code for a new function called overwritten_function and save to {SAMPLE_FILE_NAME}"
    )
    if task_id_cg_overwrite_sample:
        print(f"[Main] Orchestrator accepted CG request (overwrite sample file), Task ID: {task_id_cg_overwrite_sample}")

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

    # --- Test RefactoringAgent ---
    print("\n--- Simulating User Requests for Refactoring Agent ---")

    # Test case 1: Valid rename request
    task_id_refactor1 = await orchestrator.receive_user_request(
        request_text=f"refactor rename foo to bar in file {SAMPLE_FILE_NAME}"
        # Orchestrator's test hook should parse this and populate task.data.
        # SAMPLE_FILE_NAME is "sample_code.py" which should exist.
    )
    if task_id_refactor1:
        print(f"[Main] Orchestrator accepted request (expected RefactoringAgent, valid), Task ID: {task_id_refactor1}")

    # Test case 2: Rename request that will be missing parts for the test hook to parse fully,
    # leading to missing keys for orchestrator validation against RefactoringAgent's capability.
    task_id_refactor2 = await orchestrator.receive_user_request(
        request_text="refactor rename old_widget"
        # This is missing "to new_name" and "in file ..." structure.
        # The hook will fail to parse, task.data won't have all required keys for 'refactor_rename_variable'.
    )
    if task_id_refactor2:
        print(f"[Main] Orchestrator accepted request (expected RefactoringAgent, but to fail orchestrator validation), Task ID: {task_id_refactor2}")

    # --- Test DocumentationAgent ---
    print("\n--- Simulating User Requests for Documentation Agent ---")

    # Test case 1: Valid docstring generation request
    task_id_doc1 = await orchestrator.receive_user_request(
        request_text=f"generate docstring for {SAMPLE_FUNCTION_NAME} in file {SAMPLE_FILE_NAME}"
        # Orchestrator's test hook should parse this and populate task.data.
    )
    if task_id_doc1:
        print(f"[Main] Orchestrator accepted request (expected DocumentationAgent, valid), Task ID: {task_id_doc1}")

    # Test case 2: Request missing file_path (should fail in DocumentationAgent's _process_task or orchestrator validation)
    task_id_doc2 = await orchestrator.receive_user_request(
        request_text=f"generate docstring for {SAMPLE_FUNCTION_NAME}"
    )
    if task_id_doc2:
        print(f"[Main] Orchestrator accepted request (expected DocumentationAgent, agent to fail on missing file_path), Task ID: {task_id_doc2}")

    # Test case 3: Request missing function_name (should fail in DocumentationAgent's _process_task or orchestrator validation)
    task_id_doc3 = await orchestrator.receive_user_request(
        request_text=f"generate docstring in file {SAMPLE_FILE_NAME}"
    )
    if task_id_doc3:
        print(f"[Main] Orchestrator accepted request (expected DocumentationAgent, agent/orchestrator to fail on missing func_name), Task ID: {task_id_doc3}")

    # --- Test VersionControlAgent ---
    print("\n--- Simulating User Requests for Version Control Agent ---")

    # Test case 1: Git status request
    task_id_vcs1 = await orchestrator.receive_user_request(
        request_text="git status"
        # Orchestrator's test hook should ensure 'description' is in task.data.
        # ProjectContext in Orchestrator is currently hardcoded without vcs_type,
        # so agent should report VCS type not specified or default to non-git behavior.
    )
    if task_id_vcs1:
        print(f"[Main] Orchestrator accepted request (expected VersionControlAgent), Task ID: {task_id_vcs1}")

    # Test case 2: Generic VCS status request
    task_id_vcs2 = await orchestrator.receive_user_request(
        request_text="vcs status please"
    )
    if task_id_vcs2:
        print(f"[Main] Orchestrator accepted request (expected VersionControlAgent), Task ID: {task_id_vcs2}")

    # --- Test VulnerabilityScanAgent ---
    print("\n--- Simulating User Requests for VulnerabilityScan Agent ---")

    # Test case 1: Scan sample_code.py (expected to find a simulated vulnerability)
    task_id_vuln1 = await orchestrator.receive_user_request(
        request_text=f"scan vulnerabilities in {SAMPLE_FILE_NAME}"
        # Orchestrator's test hook should populate task.data.
        # SAMPLE_FILE_NAME is "sample_code.py".
    )
    if task_id_vuln1:
        print(f"[Main] Orchestrator accepted request (expected VulnScanAgent, finds 'sample'), Task ID: {task_id_vuln1}")

    # Test case 2: Scan README.md (expected to find no simulated vulnerability)
    task_id_vuln2 = await orchestrator.receive_user_request(
        request_text="scan file README.md for vulnerabilities"
    )
    if task_id_vuln2:
        print(f"[Main] Orchestrator accepted request (expected VulnScanAgent, no 'sample'), Task ID: {task_id_vuln2}")

    # Test case 3: Scan with missing path (should fail orchestrator validation or agent validation)
    task_id_vuln3 = await orchestrator.receive_user_request(
        request_text="scan vulnerabilities"
    )
    if task_id_vuln3:
        print(f"[Main] Orchestrator accepted request (expected VulnScanAgent, missing path), Task ID: {task_id_vuln3}")

    # --- Test EnvironmentManagementAgent ---
    print("\n--- Simulating User Requests for Environment Management Agent ---")

    # Test case 1: List dependencies
    task_id_env1 = await orchestrator.receive_user_request(
        request_text="list python dependencies"
    )
    if task_id_env1:
        print(f"[Main] Orchestrator accepted request (expected EnvMgmtAgent, list deps), Task ID: {task_id_env1}")

    # Test case 2: Install a package
    task_id_env2 = await orchestrator.receive_user_request(
        request_text="install package requests version 2.28"
    )
    if task_id_env2:
        print(f"[Main] Orchestrator accepted request (expected EnvMgmtAgent, install pkg), Task ID: {task_id_env2}")

    # Test case 3: Create a virtual environment
    task_id_env3 = await orchestrator.receive_user_request(
        request_text="create venv .myenv python 3.9"
    )
    if task_id_env3:
        print(f"[Main] Orchestrator accepted request (expected EnvMgmtAgent, create venv), Task ID: {task_id_env3}")

    # Test case 4: Dependency management with missing package name
    task_id_env4 = await orchestrator.receive_user_request(
        request_text="add package version 1.0"
    )
    if task_id_env4:
        print(f"[Main] Orchestrator accepted request (expected EnvMgmtAgent, missing pkg name for add), Task ID: {task_id_env4}")

    # Test case 5: Create venv with missing path
    task_id_env5 = await orchestrator.receive_user_request(
        request_text="create venv"
    )
    if task_id_env5:
        print(f"[Main] Orchestrator accepted request (expected EnvMgmtAgent, missing venv path), Task ID: {task_id_env5}")

    # --- Test KnowledgeBaseAgent ---
    print("\n--- Simulating User Requests for KnowledgeBase Agent ---")

    # Test case 1: Query that should find a simulated result ("novapilot")
    task_id_kb1 = await orchestrator.receive_user_request(
        request_text="query kb for novapilot architecture details"
        # Orchestrator's test hook should populate task.data.
    )
    if task_id_kb1:
        print(f"[Main] Orchestrator accepted request (expected KB Agent, finds 'novapilot'), Task ID: {task_id_kb1}")

    # Test case 2: Query that should find another simulated result ("hello")
    task_id_kb2 = await orchestrator.receive_user_request(
        request_text="query kb for hello world"
    )
    if task_id_kb2:
        print(f"[Main] Orchestrator accepted request (expected KB Agent, finds 'hello'), Task ID: {task_id_kb2}")

    # Test case 3: Query that should find no simulated results
    task_id_kb3 = await orchestrator.receive_user_request(
        request_text="query kb for unknown topic"
    )
    if task_id_kb3:
        print(f"[Main] Orchestrator accepted request (expected KB Agent, no results), Task ID: {task_id_kb3}")

    # Test case 4: Query with missing query string (should fail orchestrator validation or agent validation)
    task_id_kb4 = await orchestrator.receive_user_request(
        request_text="query kb for" # Hook might parse empty query_string or fail parsing
    )
    if task_id_kb4:
        print(f"[Main] Orchestrator accepted request (expected KB Agent, missing query string), Task ID: {task_id_kb4}")

    # --- Test AgentLifecycleManagerAgent ---
    print("\n--- Simulating User Requests for Agent Lifecycle Manager ---")

    # Test case 1: Start an agent
    DUMMY_AGENT_TO_START = "some_new_agent_id_123"
    task_id_lc1 = await orchestrator.receive_user_request(
        request_text=f"lifecycle start agent {DUMMY_AGENT_TO_START}"
        # Orchestrator's test hook should populate task.data.
    )
    if task_id_lc1:
        print(f"[Main] Orchestrator accepted request (expected LifecycleManager, start agent), Task ID: {task_id_lc1}")

    # Test case 2: Stop an agent with a reason
    DUMMY_AGENT_TO_STOP = "another_agent_id_456"
    task_id_lc2 = await orchestrator.receive_user_request(
        request_text=f"lifecycle stop agent {DUMMY_AGENT_TO_STOP} reason performing_maintenance"
    )
    if task_id_lc2:
        print(f"[Main] Orchestrator accepted request (expected LifecycleManager, stop agent), Task ID: {task_id_lc2}")

    # Test case 3: Start agent with missing agent ID in request (should fail validation)
    task_id_lc3 = await orchestrator.receive_user_request(
        request_text="lifecycle start agent"
        # Hook will fail to parse target_agent_id_to_start
    )
    if task_id_lc3:
        print(f"[Main] Orchestrator accepted request (expected LifecycleManager, missing target for start), Task ID: {task_id_lc3}")

    # Test case 4: Stop agent with missing agent ID
    task_id_lc4 = await orchestrator.receive_user_request(
        request_text="lifecycle stop agent because testing"
    )
    if task_id_lc4:
        print(f"[Main] Orchestrator accepted request (expected LifecycleManager, missing target for stop), Task ID: {task_id_lc4}")

    # --- Test AgentSandboxAgent ---
    print("\n--- Simulating User Requests for Agent Sandbox ---")

    # Test case 1: Execute simple Python print
    task_id_sb1 = await orchestrator.receive_user_request(
        request_text="sandbox execute python code 'print(\"Hello from Sandbox!\")'"
    )
    if task_id_sb1:
        print(f"[Main] Orchestrator accepted request (Sandbox: execute Python print), Task ID: {task_id_sb1}")

    # Test case 2: Execute Python code that implies an error
    task_id_sb2 = await orchestrator.receive_user_request(
        request_text="sandbox execute python code 'x = 1 / 0 # error!'"
    )
    if task_id_sb2:
        print(f"[Main] Orchestrator accepted request (Sandbox: execute Python error), Task ID: {task_id_sb2}")

    # Test case 3: Execute with missing code string
    task_id_sb3 = await orchestrator.receive_user_request(
        request_text="sandbox execute python code" # Missing the actual code
    )
    if task_id_sb3:
        print(f"[Main] Orchestrator accepted request (Sandbox: execute missing code), Task ID: {task_id_sb3}")

    # Test case 4: Manage sandbox - create
    task_id_sb4 = await orchestrator.receive_user_request(
        request_text="sandbox create my_secure_env"
    )
    if task_id_sb4:
        print(f"[Main] Orchestrator accepted request (Sandbox: manage create), Task ID: {task_id_sb4}")

    # Test case 5: Manage sandbox - delete
    task_id_sb5 = await orchestrator.receive_user_request(
        request_text="sandbox delete old_sandbox_123"
    )
    if task_id_sb5:
        print(f"[Main] Orchestrator accepted request (Sandbox: manage delete), Task ID: {task_id_sb5}")

    # Test case 6: Manage sandbox with missing action
    task_id_sb6 = await orchestrator.receive_user_request(
        request_text="sandbox my_env_details" # Missing create/delete/get_status
    )
    if task_id_sb6:
        print(f"[Main] Orchestrator accepted request (Sandbox: manage missing action), Task ID: {task_id_sb6}")

    print("\n--- Allowing time for task processing (approx 4 seconds) ---")
    await asyncio.sleep(4)

    print("\n--- Checking Task Statuses in Orchestrator ---")
    tasks_to_check = [
        task_id_cg1, task_id_cu1, task_id_cg2, task_id_cu2,
        task_id_unroutable, task_id_invalid_input,
        # task_id_cg_non_editable, task_id_cg_editable, # Superseded by more specific tests below
        task_id_completion1,
        task_id_debug1, task_id_debug2,
        task_id_test1, task_id_test2, task_id_test3,
        task_id_refactor1, task_id_refactor2,
        task_id_doc1, task_id_doc2, task_id_doc3,
        task_id_vcs1, task_id_vcs2,
        task_id_vuln1, task_id_vuln2, task_id_vuln3,
        task_id_env1, task_id_env2, task_id_env3, task_id_env4, task_id_env5,
        task_id_kb1, task_id_kb2, task_id_kb3, task_id_kb4,
        task_id_lc1, task_id_lc2, task_id_lc3, task_id_lc4,
        task_id_sb1, task_id_sb2, task_id_sb3, task_id_sb4, task_id_sb5, task_id_sb6,
        # Add new/repurposed CG task IDs
        task_id_cg_non_editable_write,
        task_id_cg_editable_write,
        task_id_cg_new_file,
        task_id_cg_overwrite_sample
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
    await vuln_scanner.stop_listening()
    await env_manager.stop_listening()
    await platform_integrator.stop_listening()
    await kb_manager.stop_listening()
    await lifecycle_mgr.stop_listening()
    await sandbox_mgr.stop_listening()
    await guardrail_checker.stop_listening()
    await evaluator.stop_listening()

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
        documenter_listener_task,
        vcs_handler_listener_task,
        vuln_scanner_listener_task,
        env_manager_listener_task,
        platform_integrator_listener_task,
        kb_manager_listener_task,
        lifecycle_mgr_listener_task,
        sandbox_mgr_listener_task,
        guardrail_listener_task,        # New or ensure present
        evaluator_listener_task,          # New or ensure present
        return_exceptions=True
    )

    print("\n--- Smart Routing Agent Interaction Example Finished ---")

if __name__ == "__main__":
    asyncio.run(main())
