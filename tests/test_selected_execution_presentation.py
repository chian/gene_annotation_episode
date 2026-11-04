from copy import deepcopy

import pytest

from gene_annotation_episode.scientific_process_prompt import (
    render_scientific_process_prompt, render_selected_execution_prompt,
)
from gene_annotation_episode.schema_information_text import parse_schema_information


@pytest.mark.parametrize("scope", [
    {"subject_refs": ["input_d215f83b2dcd345a53e168b6"]},
    {"subject_refs": ["input_d215f83b2dcd345a53e168b6"],
     "regions": [{"start": 0, "end": 4, "coordinate_unit": "residue"}]},
])
def test_assigned_scope_and_full_task_survive_each_execution_iteration(scope):
    state = {
        "goal": {"objective": "Evaluate the supplied, selected coordinate pairs."},
        "scope": scope,
        "selected_execution_task": {
            "version": "selected_execution_task_v1",
            "scientific_question": "What is the RMSD over the selected evaluation pairs?",
            "selected_tool_info": [],
            "requests": [{
                "resource_id": "selected_local",
                "resource_kind": "local",
                "constraints": {},
                "resource": {"kind": "local"},
                "job": {"operation": "compare"},
            }],
            "constraints": {"evaluation_selection": "supplied_pairs_only"},
        },
    }
    instructions = "Preserve the assigned coordinate selection and requested quantities."
    original = deepcopy(state)
    first = render_selected_execution_prompt(state, instructions)
    assert state == original

    state["action_yields"] = {"rows": [{
        "category": "tool", "completed_actions": 1, "total_yield": 0.25,
        "attempted_uncompleted": 0,
        "expected_yield": {"band": {"value": 0.1, "lower": 0.0, "upper": 0.2}},
    }]}
    next_state = deepcopy(state)
    second = render_selected_execution_prompt(state, instructions)
    assert state == next_state

    first_task, first_steering = first.split("\n\nSTEERING", 1)
    second_task, second_steering = second.split("\n\nSTEERING", 1)
    assert first_task == second_task
    assert scope["subject_refs"][0] in first_task
    assert "What is the RMSD over the selected evaluation pairs?" in first_task
    assert "supplied_pairs_only" in first_task
    assert instructions in first_task
    if "regions" in scope:
        assert "regions[0].start" in first_task
        assert "regions[0].end" in first_task
        assert "residue" in first_task
    assert "0.25" in second_steering
    assert first_steering != second_steering


def test_caller_schema_identities_and_relative_references_remain_in_scientific_task():
    state = {
        "goal": {"objective": "Read the retained selected distance measurement."},
        "scientific_process": {
            "evidence_axis": {
                "name": "Structural homology",
                "instruction_status": "published_investigation_instructions",
                "investigation_instructions": "Preserve matched extent and distance units.",
            },
        },
        "tools": [{
            "name": "selected.measurement",
            "description": "Read an explicitly selected retained measurement.",
            "input_schema": {
                "$id": "https://caller.example/contracts/structure.json",
                "type": "object",
                "$defs": {"distance": {
                    "$id": "distance.json",
                    "type": ["number", "null"],
                    "description": "RMSD in angstrom", "minimum": 0,
                }},
                "properties": {"rmsd": {"$ref": "distance.json"}},
                "required": ["rmsd"], "additionalProperties": False,
            },
        }],
    }
    original = deepcopy(state)
    text = render_scientific_process_prompt(state, "Read the assigned measurement.")
    assert state == original
    # Caller identities can determine relative-reference meaning. They are not
    # host bookkeeping pins; the schema presentation retains the entire tree.
    start = text.index("Schema information\n")
    end = text.index("End schema information\n", start) + len("End schema information\n")
    assert parse_schema_information(text[start:end]) == state["tools"][0]["input_schema"]
