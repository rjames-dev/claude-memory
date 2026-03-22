#!/usr/bin/env python3
"""
Claude Memory - Skills System: Integration Test Suite

Comprehensive integration testing for the Skills System.

Tests:
- Complete workflows (create → list → info → execute)
- Database consistency
- Edge cases and error conditions
- All output formats
- Performance tracking

Usage:
    python3 test-skills-integration.py [--cleanup]

Arguments:
    --cleanup    Remove test skills after testing (default: keep for inspection)
"""

import sys
import os
import subprocess
import json
import argparse
import time
from datetime import datetime

# Script location for portable path resolution
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Test configuration
TEST_SKILL_PREFIX = f"test-integration-{int(time.time())}-"
VERBOSE = True

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class TestResult:
    """Track test results."""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, test_name):
        self.total += 1
        self.passed += 1
        print(f"{GREEN}✓{RESET} {test_name}")

    def add_fail(self, test_name, error):
        self.total += 1
        self.failed += 1
        self.errors.append((test_name, error))
        print(f"{RED}✗{RESET} {test_name}")
        print(f"  Error: {error}")

    def print_summary(self):
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.total}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")

        if self.failed > 0:
            print(f"\n{RED}Failed Tests:{RESET}")
            for test_name, error in self.errors:
                print(f"  - {test_name}: {error}")

        print("="*80)

        return self.failed == 0


def run_command(cmd, description=None, should_succeed=True):
    """Run a command and return result."""
    if VERBOSE and description:
        print(f"{BLUE}→{RESET} {description}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        if should_succeed and result.returncode != 0:
            return None, f"Command failed with exit code {result.returncode}: {result.stderr[:200]}"

        return result, None

    except subprocess.TimeoutExpired:
        return None, "Command timed out"
    except Exception as e:
        return None, f"Exception: {str(e)}"


def setup_environment():
    """Setup test environment."""
    password = os.environ.get('CONTEXT_DB_PASSWORD')
    if not password:
        print(f"{RED}Error: CONTEXT_DB_PASSWORD not set{RESET}")
        sys.exit(1)

    return password


def test_skill_creation(results, password):
    """Test skill creation functionality."""
    print(f"\n{YELLOW}=== Testing Skill Creation ==={RESET}")

    # Test 1: Create valid skill
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 create-skill.py \
        --name "{TEST_SKILL_PREFIX}basic" \
        --display-name "Test Basic Skill" \
        --category "testing" \
        --description "Basic integration test skill" \
        --command-type "bash_script" \
        --script-content 'echo "Test passed"' \
        --triggers "test basic"
    """

    result, error = run_command(cmd, "Create basic test skill")
    if error:
        results.add_fail("Create basic skill", error)
    elif "✅ Skill created:" not in result.stdout:
        results.add_fail("Create basic skill", "Success message not found")
    else:
        results.add_pass("Create basic skill")

    # Test 2: Duplicate skill rejection
    result, error = run_command(cmd, "Test duplicate rejection", should_succeed=False)
    if result and result.returncode == 0:
        results.add_fail("Reject duplicate skill", "Should have rejected duplicate")
    elif result and "already exists" in result.stderr:
        results.add_pass("Reject duplicate skill")
    else:
        results.add_fail("Reject duplicate skill", "Unexpected error")

    # Test 3: Invalid skill name rejection
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 create-skill.py \
        --name "Invalid Name With Spaces" \
        --display-name "Invalid" \
        --category "testing" \
        --description "Test" \
        --command-type "bash_script" \
        --script-content 'echo test' \
        --triggers "test"
    """

    result, error = run_command(cmd, "Test invalid name rejection", should_succeed=False)
    if result and result.returncode == 0:
        results.add_fail("Reject invalid skill name", "Should have rejected invalid name")
    elif result and "kebab-case" in result.stderr:
        results.add_pass("Reject invalid skill name")
    else:
        results.add_fail("Reject invalid skill name", "Unexpected error")

    # Test 4: Create skill with parameters
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 create-skill.py \
        --name "{TEST_SKILL_PREFIX}params" \
        --display-name "Test Parameters" \
        --category "testing" \
        --description "Test skill with parameters" \
        --command-type "bash_script" \
        --script-content 'echo "Param test"' \
        --triggers "test params" \
        --parameters '{{"timeout": {{"type": "integer", "default": 30}}}}'
    """

    result, error = run_command(cmd, "Create skill with parameters")
    if error:
        results.add_fail("Create skill with parameters", error)
    elif "✅ Skill created:" not in result.stdout:
        results.add_fail("Create skill with parameters", "Success message not found")
    else:
        results.add_pass("Create skill with parameters")


def test_skill_listing(results, password):
    """Test skill listing functionality."""
    print(f"\n{YELLOW}=== Testing Skill Listing ==={RESET}")

    # Test 1: List all skills (table format)
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 list-skills.py
    """

    result, error = run_command(cmd, "List all skills (table format)")
    if error:
        results.add_fail("List skills - table format", error)
    elif TEST_SKILL_PREFIX not in result.stdout:
        results.add_fail("List skills - table format", "Test skills not found")
    else:
        results.add_pass("List skills - table format")

    # Test 2: List skills (JSON format)
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 list-skills.py --format json
    """

    result, error = run_command(cmd, "List skills (JSON format)")
    if error:
        results.add_fail("List skills - JSON format", error)
    else:
        try:
            data = json.loads(result.stdout)
            if isinstance(data, list) and len(data) > 0:
                results.add_pass("List skills - JSON format")
            else:
                results.add_fail("List skills - JSON format", "Invalid JSON structure")
        except json.JSONDecodeError as e:
            results.add_fail("List skills - JSON format", f"Invalid JSON: {e}")

    # Test 3: Filter by category
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 list-skills.py --category testing
    """

    result, error = run_command(cmd, "Filter skills by category")
    if error:
        results.add_fail("Filter by category", error)
    elif TEST_SKILL_PREFIX not in result.stdout:
        results.add_fail("Filter by category", "Test skills not found")
    else:
        results.add_pass("Filter by category")

    # Test 4: Sort by name
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 list-skills.py --sort name --format compact
    """

    result, error = run_command(cmd, "Sort skills by name")
    if error:
        results.add_fail("Sort by name", error)
    else:
        results.add_pass("Sort by name")

    # Test 5: Limit results
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 list-skills.py --limit 2 --format json
    """

    result, error = run_command(cmd, "Limit results")
    if error:
        results.add_fail("Limit results", error)
    else:
        try:
            data = json.loads(result.stdout)
            if len(data) <= 2:
                results.add_pass("Limit results")
            else:
                results.add_fail("Limit results", f"Expected ≤2 results, got {len(data)}")
        except json.JSONDecodeError:
            results.add_fail("Limit results", "Invalid JSON")


def test_skill_info(results, password):
    """Test skill info functionality."""
    print(f"\n{YELLOW}=== Testing Skill Info ==={RESET}")

    # Test 1: Get skill info by name
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 skill-info.py {TEST_SKILL_PREFIX}basic
    """

    result, error = run_command(cmd, "Get skill info by name")
    if error:
        results.add_fail("Get skill info by name", error)
    elif "SKILL INFORMATION" not in result.stdout:
        results.add_fail("Get skill info by name", "Info header not found")
    else:
        results.add_pass("Get skill info by name")

    # Test 2: Get skill info (JSON format)
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 skill-info.py {TEST_SKILL_PREFIX}basic --format json
    """

    result, error = run_command(cmd, "Get skill info (JSON)")
    if error:
        results.add_fail("Get skill info - JSON", error)
    else:
        try:
            data = json.loads(result.stdout)
            if 'skill' in data and 'triggers' in data and 'command' in data:
                results.add_pass("Get skill info - JSON")
            else:
                results.add_fail("Get skill info - JSON", "Missing expected keys")
        except json.JSONDecodeError as e:
            results.add_fail("Get skill info - JSON", f"Invalid JSON: {e}")

    # Test 3: Show full script
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 skill-info.py {TEST_SKILL_PREFIX}basic --show-script
    """

    result, error = run_command(cmd, "Show full script content")
    if error:
        results.add_fail("Show full script", error)
    elif "Script Content:" not in result.stdout:
        results.add_fail("Show full script", "Script content section not found")
    else:
        results.add_pass("Show full script")

    # Test 4: Nonexistent skill
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 skill-info.py nonexistent-skill-xyz
    """

    result, error = run_command(cmd, "Get info for nonexistent skill", should_succeed=False)
    if result and result.returncode == 0:
        results.add_fail("Nonexistent skill error", "Should have failed")
    elif result and "not found" in result.stderr:
        results.add_pass("Nonexistent skill error")
    else:
        results.add_fail("Nonexistent skill error", "Unexpected error")


def test_skill_execution(results, password):
    """Test skill execution functionality."""
    print(f"\n{YELLOW}=== Testing Skill Execution ==={RESET}")

    # Test 1: Dry run
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 execute-skill.py {TEST_SKILL_PREFIX}basic --dry-run
    """

    result, error = run_command(cmd, "Dry run execution")
    if error:
        results.add_fail("Dry run execution", error)
    elif "DRY RUN MODE" not in result.stdout:
        results.add_fail("Dry run execution", "Dry run message not found")
    else:
        results.add_pass("Dry run execution")

    # Test 2: Execute skill successfully
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 execute-skill.py {TEST_SKILL_PREFIX}basic --time-saved 10
    """

    result, error = run_command(cmd, "Execute skill successfully")
    if error:
        results.add_fail("Execute skill", error)
    elif "✅ Skill executed successfully" not in result.stdout:
        results.add_fail("Execute skill", "Success message not found")
    elif "Test passed" not in result.stdout:
        results.add_fail("Execute skill", "Expected output not found")
    else:
        results.add_pass("Execute skill")

    # Test 3: Verify counters updated
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 skill-info.py {TEST_SKILL_PREFIX}basic --format json
    """

    result, error = run_command(cmd, "Verify counters after execution")
    if error:
        results.add_fail("Verify execution counters", error)
    else:
        try:
            data = json.loads(result.stdout)
            skill = data['skill']
            if skill['use_count'] >= 1 and skill['success_count'] >= 1:
                results.add_pass("Verify execution counters")
            else:
                results.add_fail("Verify execution counters", f"use_count={skill['use_count']}, success_count={skill['success_count']}")
        except (json.JSONDecodeError, KeyError) as e:
            results.add_fail("Verify execution counters", f"Parse error: {e}")

    # Test 4: Create and execute failing skill
    create_cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 create-skill.py \
        --name "{TEST_SKILL_PREFIX}fail" \
        --display-name "Test Failure" \
        --category "testing" \
        --description "Skill that fails" \
        --command-type "bash_script" \
        --script-content 'echo "Failing"; exit 1' \
        --triggers "test fail"
    """

    result, error = run_command(create_cmd, "Create failing skill")
    if error:
        results.add_fail("Create failing skill", error)
        return

    exec_cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 execute-skill.py {TEST_SKILL_PREFIX}fail --time-saved 5
    """

    result, error = run_command(exec_cmd, "Execute failing skill", should_succeed=False)
    if result and result.returncode == 0:
        results.add_fail("Failing skill execution", "Should have failed")
    elif result and "❌ Skill execution failed" in result.stdout:
        results.add_pass("Failing skill execution")
    else:
        results.add_fail("Failing skill execution", "Unexpected error")

    # Test 5: Verify failure counter
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 skill-info.py {TEST_SKILL_PREFIX}fail --format json
    """

    result, error = run_command(cmd, "Verify failure counter")
    if error:
        results.add_fail("Verify failure counter", error)
    else:
        try:
            data = json.loads(result.stdout)
            skill = data['skill']
            if skill['failure_count'] >= 1:
                results.add_pass("Verify failure counter")
            else:
                results.add_fail("Verify failure counter", f"failure_count={skill['failure_count']}")
        except (json.JSONDecodeError, KeyError) as e:
            results.add_fail("Verify failure counter", f"Parse error: {e}")


def test_complete_workflow(results, password):
    """Test complete workflow end-to-end."""
    print(f"\n{YELLOW}=== Testing Complete Workflow ==={RESET}")

    workflow_skill = f"{TEST_SKILL_PREFIX}workflow"

    # Step 1: Create skill
    create_cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 create-skill.py \
        --name "{workflow_skill}" \
        --display-name "Workflow Test" \
        --category "testing" \
        --description "End-to-end workflow test" \
        --command-type "bash_script" \
        --script-content 'echo "Workflow complete"' \
        --triggers "test workflow,workflow test"
    """

    result, error = run_command(create_cmd, "Workflow: Create skill")
    if error:
        results.add_fail("Workflow - create", error)
        return

    # Step 2: List and verify
    list_cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 list-skills.py --format json
    """

    result, error = run_command(list_cmd, "Workflow: List skills")
    if error:
        results.add_fail("Workflow - list", error)
        return

    try:
        data = json.loads(result.stdout)
        found = any(s['agent_name'] == workflow_skill for s in data)
        if not found:
            results.add_fail("Workflow - list", "Skill not found in list")
            return
    except json.JSONDecodeError:
        results.add_fail("Workflow - list", "Invalid JSON")
        return

    # Step 3: Get info
    info_cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 skill-info.py {workflow_skill}
    """

    result, error = run_command(info_cmd, "Workflow: Get skill info")
    if error:
        results.add_fail("Workflow - info", error)
        return

    # Step 4: Execute
    exec_cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 execute-skill.py {workflow_skill} --time-saved 20
    """

    result, error = run_command(exec_cmd, "Workflow: Execute skill")
    if error:
        results.add_fail("Workflow - execute", error)
        return

    # Step 5: Verify execution in history
    info_cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 skill-info.py {workflow_skill} --format json
    """

    result, error = run_command(info_cmd, "Workflow: Verify execution")
    if error:
        results.add_fail("Workflow - verify", error)
        return

    try:
        data = json.loads(result.stdout)
        if len(data['performance_logs']) > 0:
            results.add_pass("Complete workflow (create → list → info → execute → verify)")
        else:
            results.add_fail("Workflow - verify", "No execution logs found")
    except (json.JSONDecodeError, KeyError):
        results.add_fail("Workflow - verify", "Invalid response")


def test_database_consistency(results, password):
    """Test database consistency."""
    print(f"\n{YELLOW}=== Testing Database Consistency ==={RESET}")

    # Test 1: Success rate calculation
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 skill-info.py {TEST_SKILL_PREFIX}basic --format json
    """

    result, error = run_command(cmd, "Verify success rate calculation")
    if error:
        results.add_fail("Success rate calculation", error)
    else:
        try:
            data = json.loads(result.stdout)
            skill = data['skill']

            if skill['use_count'] == 0:
                expected_rate = 0.0
            else:
                expected_rate = (skill['success_count'] / skill['use_count']) * 100

            if abs(skill['success_rate'] - expected_rate) < 0.01:
                results.add_pass("Success rate calculation")
            else:
                results.add_fail("Success rate calculation",
                    f"Expected {expected_rate:.1f}%, got {skill['success_rate']:.1f}%")
        except (json.JSONDecodeError, KeyError, ZeroDivisionError) as e:
            results.add_fail("Success rate calculation", f"Error: {e}")

    # Test 2: Trigger count consistency
    workflow_skill = f"{TEST_SKILL_PREFIX}workflow"
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 skill-info.py {workflow_skill} --format json
    """

    result, error = run_command(cmd, "Verify trigger count")
    if error:
        results.add_fail("Trigger count consistency", error)
    else:
        try:
            data = json.loads(result.stdout)
            trigger_count = len(data['triggers'])

            # Workflow skill should have 2 triggers
            if trigger_count == 2:
                results.add_pass("Trigger count consistency")
            else:
                results.add_fail("Trigger count consistency", f"Expected 2 triggers, found {trigger_count}")
        except (json.JSONDecodeError, KeyError) as e:
            results.add_fail("Trigger count consistency", f"Error: {e}")


def cleanup_test_skills(password):
    """Clean up test skills created during testing."""
    print(f"\n{YELLOW}=== Cleaning Up Test Skills ==={RESET}")

    # Get list of test skills
    cmd = f"""cd {SCRIPT_DIR} && \
        export CONTEXT_DB_PASSWORD="{password}" && \
        python3 list-skills.py --format json
    """

    result, error = run_command(cmd, "Get list of skills for cleanup")
    if error:
        print(f"{RED}Failed to get skills list: {error}{RESET}")
        return

    try:
        data = json.loads(result.stdout)
        test_skills = [s for s in data if s['agent_name'].startswith(TEST_SKILL_PREFIX)]

        if not test_skills:
            print(f"{YELLOW}No test skills to clean up{RESET}")
            return

        # Note: Deletion would require a delete-skill.py script
        # For now, just report what would be deleted
        print(f"{YELLOW}Test skills that should be cleaned up:{RESET}")
        for skill in test_skills:
            print(f"  - {skill['agent_name']} (ID: {skill['id']})")

        print(f"\n{YELLOW}Note: Skill deletion not implemented in Phase 1{RESET}")
        print(f"{YELLOW}Test skills remain in database for manual inspection{RESET}")

    except json.JSONDecodeError:
        print(f"{RED}Failed to parse skills list{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description='Integration test suite for Skills System'
    )
    parser.add_argument('--cleanup',
                        action='store_true',
                        help='Clean up test skills after testing')

    args = parser.parse_args()

    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}SKILLS SYSTEM - INTEGRATION TEST SUITE{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Setup
    password = setup_environment()
    results = TestResult()

    # Run test suites
    test_skill_creation(results, password)
    test_skill_listing(results, password)
    test_skill_info(results, password)
    test_skill_execution(results, password)
    test_complete_workflow(results, password)
    test_database_consistency(results, password)

    # Cleanup
    if args.cleanup:
        cleanup_test_skills(password)

    # Print summary
    print()
    success = results.print_summary()

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
