---
name: unit-test
description: |
  Generates, executes, and reports on Python unit tests using pytest.
  Triggered when the user runs /unit-test or asks to write/run unit tests or generate a test report.
---

# Unit Test Skill

This skill automates the process of generating unit tests for a specified code file, executing them using `pytest`, and outputting a formatted Markdown test report.

## When to use

Use this skill when:
- The user or subagent types `/unit-test <file_path>` or asks to test a specific code file.
- The user or subagent requests a "unit test report" or wants to "run tests".

## Instruction Steps

When this skill is triggered, perform the following steps:

1. **Locate Target File**:
   - Determine which file the user wants to test (e.g. `backend/app/auth.py` or similar).

2. **Generate Test Code**:
   - Write test files in the `backend/tests/` directory with the prefix `test_`.
   - Use standard `pytest` syntax.

3. **Execute Run Test Script**:
   - Run the test runner Python script. This script will execute `pytest` with the `--junitxml` parameter and automatically compile a clean Markdown report.
   - Run command format:
     ```bash
     .venv\Scripts\python .agents/plugins/testing-plugin/skills/unit-test/scripts/run_tests.py d:\Dev\langchain <test_file_or_directory_path>
     ```

4. **Present the Markdown Test Report**:
   - The test runner will output a file named `test_report.md` in the workspace root.
   - Read this file using `view_file` and display its content to the user.
