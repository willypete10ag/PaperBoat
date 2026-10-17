"""Shared paths and safety checks for portable, disposable native fixtures."""

import os
from pathlib import Path


def required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing {name}; run tools/porting/run_acceptance.sh (see README.md)")
    return value


def fixture_path(relative):
    return Path(required_env("PORTING_WORK_DIR")).resolve() / relative


def source_path(relative):
    return Path(required_env("PAPERBOAT_SOURCE_DIR")).resolve() / relative


def reference_path(relative):
    return Path(required_env("TTYD64_REFERENCE_DIR")).resolve() / relative


def fixture_save():
    return Path(required_env("PORTING_SAVE_DIR")).resolve() / "file3.json"


def validate_runtime():
    runtime = Path(required_env("SHIP_HOME")).resolve()
    work = Path(required_env("PORTING_WORK_DIR")).resolve()
    saves = Path(required_env("PORTING_SAVE_DIR")).resolve()
    if not runtime.is_relative_to(work) or saves != runtime / "saves":
        raise RuntimeError("Fixture SHIP_HOME and PORTING_SAVE_DIR must belong to the disposable PORTING_WORK_DIR")
    marker = runtime / ".porting-disposable"
    if not marker.is_file() or marker.read_text() != "PaperBoat acceptance runtime v1\n":
        raise RuntimeError("Refusing an unowned runtime: missing acceptance marker")


# Record how checks were driven. Native input is explicitly distinguished from
# debugger setup, API calls, forced returns and predicate-only observations.
import json
import re

_events = []
_records = []


def record_check(name, driver=None, note=None):
    global _events
    events = list(dict.fromkeys(_events))
    forced = [e for e in events if e.startswith("forced_return:")]
    category = (
        "forced_debugger_return"
        if forced
        else (
            "real_input_after_debugger_setup"
            if "keyboard_input" in events
            else ("controlled_api_or_state" if events else "predicate")
        )
    )
    _records.append(
        {
            "check": name,
            "driver": driver or category,
            "note": note,
            "fixture_uses_debugger_setup": True,
            "events_since_previous_check": events,
        }
    )
    _events = []
    Path(required_env("PORTING_CHECK_METHODS")).write_text(json.dumps(_records, indent=2) + "\n")


try:
    import gdb

    _execute = gdb.execute
    _evaluate = gdb.parse_and_eval

    def _audited_execute(command, *args, **kwargs):
        stripped = command.strip()
        if stripped == "return" or stripped.startswith("return "):
            _events.append("forced_return:" + stripped[6:].strip())
        elif stripped.startswith(("set variable ", "set $", "call ", "jump ")):
            _events.append("debugger_state_or_api")
        return _execute(command, *args, **kwargs)

    def _audited_evaluate(expression, *args, **kwargs):
        if re.search(r"\b(?!sizeof\b)[A-Za-z_]\w*\s*\(", expression):
            _events.append("debugger_expression_api")
        return _evaluate(expression, *args, **kwargs)

    gdb.execute = _audited_execute
    gdb.parse_and_eval = _audited_evaluate
    import subprocess

    _run = subprocess.run

    def _audited_run(command, *args, **kwargs):
        if (
            isinstance(command, list)
            and command
            and command[0] == "xdotool"
            and any(k in command for k in ("keydown", "key", "keyup"))
        ):
            _events.append("keyboard_input")
        return _run(command, *args, **kwargs)

    subprocess.run = _audited_run
except ImportError:
    pass
