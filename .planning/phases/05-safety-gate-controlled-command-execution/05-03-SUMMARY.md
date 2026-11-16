# Phase 5 Plan 03: Inline Command Editing & CLI/REPL Safety Gate Integration Summary

## Work Completed
1. **Inline Command Buffer Editor (`prompt_edit_command`)**:
   - Implemented `prompt_edit_command` in `src/aishell/safety/gate.py` with pre-loaded command buffer via `prompt_toolkit.prompt(default=initial_command)` per D-04 and EXEC-03.
   - Preserved full cursor navigation, readline/emacs/vi editing shortcuts, and backspace deletion.
   - Handled empty submission, Ctrl+C (KeyboardInterrupt), and Ctrl+D (EOFError) gracefully.
2. **SafetyGate Service Orchestrator (`SafetyGate`)**:
   - Implemented `SafetyGate.process_proposal()` orchestrating the complete lifecycle:
     - Reconciles proposal risk tier with deterministic client-side heuristics.
     - Renders proposal card via `render_proposal`.
     - Prompts operator via `prompt_confirmation` with `[y/N/e]` gate.
     - On `GateAction.CONFIRM`: returns approved command.
     - On `GateAction.EDIT`: launches inline editor, re-evaluates risk tier on modified command, displays updated proposal card, and prompts confirmation again.
     - On `GateAction.CANCEL`: cleanly returns `None` without side effects.
3. **CLI One-Shot Integration (`src/aishell/cli.py`)**:
   - Updated `execute_one_shot()` to extract proposals from model stream output.
   - If proposal contains an executable command, passed through `SafetyGate.process_proposal()`.
   - Only runs `execute_pipeline()` if explicitly confirmed by operator.
4. **Interactive REPL Integration (`src/aishell/ui/repl.py`)**:
   - Initialized `self.safety_gate` in `InteractiveREPL.__init__`.
   - Updated `dispatch_input()` natural language path to extract proposals from model output stream and gate them through `self.safety_gate.process_proposal()`.
   - Executed confirmed commands via `self.executor_fn` or `execute_pipeline()`.
   - Direct shell commands (prefixed with `!` or `$`) continue to execute directly without gating per Phase 2 design.
5. **Testing**:
   - Created `tests/test_cli_safety.py` (3 tests).
   - Created `tests/test_repl_safety.py` (4 tests).
   - Added `test_prompt_edit_command_success`, `test_prompt_edit_command_cancel`, and `test_safety_gate_service_*` to `tests/test_safety_gate.py`.
   - Full workspace test suite runs 153 tests with 100% pass rate.

## Verification
- `uv run pytest tests/test_cli_safety.py tests/test_repl_safety.py tests/test_safety_gate.py -v` passed.
- Full workspace test suite: 153 passed in 15.44s.
