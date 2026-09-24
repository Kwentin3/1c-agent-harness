"""Hermes registration for the terminal-bound 1C Harness capability."""
from pathlib import Path

from .adapter import (
    expand_observation, narrow_context, native_verify, observation_info, observe, open_target,
    page_registration_log, read_registration_log_record, select_registration_log,
)
from .schemas import TOOLS

_SYSTEM_RULES = (
    "The one-c-harness plugin is a thin terminal-bound adapter. Use one_c_open first for "
    "configuration work and pass its exact snapshotRef to one_c_narrow_context or "
    "one_c_native_verify; never substitute a path. For technological-journal work, use "
    "one_c_observation_info when the available interval is unknown, then preserve exact "
    "observationRef/groupRef/recordRef values for paging and retained-selection neighbors. "
    "For registration-log work, preserve exact selectionRef/recordRef values, follow display.nextOffset "
    "for response paging and commentContinuation.nextOffsetBytes on the same retained record, and keep "
    "display, comment and source coverage states separate. Treat any maximum-count boundary as partial. "
    "Source unavailable is not an empty journal; use only its safe "
    "reason, stage, exit code and opaque diagnostic ref, never raw stderr. "
    "Partial discovery is not complete history, and time adjacency is not causality. The "
    "selected Hermes terminal workspace is the only project-root authority. The plugin does "
    "not manage SSH, credentials, deployment, or 1C runtime installation."
)


def register(ctx):
    handlers = {
        "one_c_open": open_target(ctx),
        "one_c_narrow_context": narrow_context(ctx),
        "one_c_native_verify": native_verify(ctx),
        "one_c_observation_info": observation_info(ctx),
        "one_c_observe": observe(ctx),
        "one_c_expand_observation": expand_observation(ctx),
        "one_c_select_registration_log": select_registration_log(ctx),
        "one_c_page_registration_log": page_registration_log(ctx),
        "one_c_read_registration_log_record": read_registration_log_record(ctx),
    }
    for schema in TOOLS:
        ctx.register_tool(
            name=schema["name"],
            toolset="one_c",
            schema=schema,
            handler=handlers[schema["name"]],
            emoji="🔎",
        )
    ctx.register_skill(
        "one-c-harness",
        Path(__file__).with_name("skills") / "one-c-harness" / "SKILL.md",
        "Use when investigating a 1C target through the terminal-bound companion.",
    )
    ctx.register_system_prompt_section(
        "one-c-harness.boundary", _SYSTEM_RULES, position="after_memory", max_chars=1000,
    )
