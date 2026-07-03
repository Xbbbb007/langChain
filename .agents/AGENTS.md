# Project Git Commit Rules

## Git Quality Gate Constraints
1. **Respect Pre-commit Hooks**: Always respect the repository's git pre-commit hooks.
2. **No Verification Bypassing**: Under no circumstances should Git commits use the `--no-verify` or `-n` flag to bypass quality checks, unless explicitly requested by the user.
3. **Handle Hook Failures**: If a commit is blocked by the pre-commit hook due to missing or failed test/quality markers, the agent must run the verification scripts first to resolve the checks:
   - Run tests: `.venv/Scripts/python .agents/plugins/testing-plugin/skills/unit-test/scripts/run_tests.py <workspace_path> backend/tests`
   - Run quality audit: `.venv/Scripts/python .agents/plugins/testing-plugin/skills/security-audit/scripts/run_quality_audit.py <workspace_path> <workspace_path>`
