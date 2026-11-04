"""One actual E2 return envelope and preserved historical validation behavior."""
from copy import deepcopy
import json

import pytest

from method_loop.durable import canonical
from method_loop.identities import UnitRef
from gene_annotation_episode.local_return_history import LocalReturnHistory
from gene_annotation_episode.wait_estimation_inputs import (
    validate_local_return_evidence, validate_local_return_history)
from test_local_return_history import Case, STAMP, LATER


INVALID = "^invalid_local_return_evidence$"
CONFLICT = "^local_return_evidence_identity_conflict$"


@pytest.fixture(scope="module")
def evidence_value(tmp_path_factory):
    directory = tmp_path_factory.mktemp("actual-e2-envelope")
    case = Case(directory)
    try:
        first = case.child(1, credit=5.0)
        case.stage(first[2])
        second = case.child(4, credit=2.0)
        case.stage(second[2])
        value = LocalReturnHistory(case.store, case.journal, case.backend).read_return(case.parent, 4)
        (directory/"original-evidence.json").write_text(json.dumps(value, indent=2)+"\n")
        yield value, {"run_id":case.journal.run_id,"episode_id":case.parent,"original_decision_index":4}
    finally:
        case.store.close()


def test_actual_read_return_signed_delta_and_detached_copy(evidence_value):
    value, arguments = evidence_value
    original = canonical(value)
    checked = validate_local_return_evidence(value, **arguments)
    assert canonical(checked) == original and checked is not value
    assert checked["sample"]["raw_controller_delta"] == -3.0
    assert checked["sample"]["unit_ref"] == UnitRef(arguments["episode_id"],1).as_record()
    checked["sample"]["controller_step"]["marginal_credit"] = 999
    assert canonical(value) == original


@pytest.mark.parametrize("state",["admitted","delivery_failed","execution_failed","receiver_closed"])
def test_actual_e2_admission_states_and_unobserved_cut(tmp_path,state):
    case=Case(tmp_path)
    try:
        item=case.child(7,state=state)
        if state in {"admitted","delivery_failed"}:
            case.stage(item[2],observe=False)
        value=LocalReturnHistory(case.store,case.journal,case.backend).read_return(case.parent,7)
        checked=validate_local_return_evidence(value,run_id=case.journal.run_id,episode_id=case.parent)
        assert checked==value and checked["sample"]["observation_state"]=="unobserved"
    finally:
        case.store.close()


@pytest.mark.parametrize("missing",["return","commission"])
def test_actual_e2_missing_original_support_stays_unknown(tmp_path,monkeypatch,missing):
    case=Case(tmp_path)
    try:
        item=case.child(7)
        case.stage(item[2])
        if missing=="commission":
            case.store.db.execute("DROP TABLE runtime_commission_intents")
        else:
            def unavailable(*args):
                raise OSError("fixture original immutable return unavailable")
            monkeypatch.setattr(case.backend,"load_return",unavailable)
        value=LocalReturnHistory(case.store,case.journal,case.backend).read_return(case.parent,7)
        assert validate_local_return_evidence(value,run_id=case.journal.run_id,episode_id=case.parent)==value
        assert value["sample"]["selection_to_return"]["seconds"] is None
        assert value["sample"]["raw_controller_delta"]==5.25
    finally:
        case.store.close()


def test_actual_negative_timestamp_difference_remains_unmeasured(tmp_path):
    case=Case(tmp_path)
    try:
        case.child(7,selected_at="2026-10-21T13:00:00+00:00",returned_at=LATER)
        value=LocalReturnHistory(case.store,case.journal,case.backend).read_return(case.parent,7)
        assert value["sample"]["selection_to_return"]=={"seconds":None,"measure":"utc_timestamp_difference",
            "unavailable_reason":"negative_selection_to_return"}
        assert validate_local_return_evidence(value,run_id=case.journal.run_id,episode_id=case.parent)==value
    finally:
        case.store.close()


def alter(value,path,replacement):
    for key in path[:-1]:value=value[key]
    value[path[-1]]=replacement


@pytest.mark.parametrize("path,replacement,error",[
    (("version",),"local_parent_return_history_v1",INVALID),
    (("extra",),None,INVALID),
    (("run_id",),"invented-envelope-field",INVALID),
    (("sample","original_decision_index"),True,INVALID),
    (("sample","original_decision_index"),99,CONFLICT),
    (("sample","admission_id"),"foreign",CONFLICT),
    (("sample","sample_ref"),"foreign",CONFLICT),
    (("sample","completion_sequence"),99,CONFLICT),
    (("sample","unit_ref","unit_id"),"foreign",INVALID),
    (("sample","raw_controller_delta"),0,CONFLICT),
    (("sample","controller_step","marginal_credit"),-9.0,CONFLICT),
    (("sample","controller_input",7),"non-string-key",INVALID),
    (("sample","controller_input","bad"),float("inf"),INVALID),
    (("sample","selection_to_return","seconds"),999,CONFLICT),
    (("sample","selected_at"),None,CONFLICT),
    (("sample","returned_at"),"2026-10-21T12:00:00-05:00",INVALID),
    (("sample","linked_waits"),[{}],INVALID),
    (("unavailable_reasons",),[""],INVALID),
])
def test_evidence_specific_closed_shapes_identities_and_timing(evidence_value,path,replacement,error):
    original,arguments=evidence_value
    value=deepcopy(original)
    alter(value,path,replacement)
    with pytest.raises(ValueError,match=error):validate_local_return_evidence(value,**arguments)


def test_evidence_foreign_unit_and_enclosing_identity(evidence_value):
    original,arguments=evidence_value
    value=deepcopy(original)
    value["sample"]["unit_ref"]=UnitRef("another-episode",1).as_record()
    with pytest.raises(ValueError,match=CONFLICT):validate_local_return_evidence(value,**arguments)
    for key in ("run_id","episode_id"):
        with pytest.raises(ValueError,match=CONFLICT):
            validate_local_return_evidence(original,**{**arguments,key:"foreign"})
    with pytest.raises(ValueError,match=INVALID):
        validate_local_return_evidence(original,**{**arguments,"original_decision_index":True})


def test_history_seam_keeps_its_original_accepted_values_and_errors(evidence_value):
    original,arguments=evidence_value
    # These historically accepted values intentionally lack the new evidence
    # identity/timing relationships. Extraction must not strengthen that API.
    sample=deepcopy(original["sample"])
    sample.update(sample_ref="legacy-admission",admission_id="legacy-admission",raw_controller_delta=123.0)
    sample["selection_to_return"]["seconds"]=999
    history={"version":"local_parent_return_history_v1","run_id":arguments["run_id"],
        "episode_id":arguments["episode_id"],"credit_kind":"scientific","credit_binding":{7:"old-json-key"},
        "samples":[sample],"unavailable_reasons":[]}
    checked=validate_local_return_history(history)
    assert checked["credit_binding"]=={"7":"old-json-key"}
    assert checked["samples"][0]==sample
    with pytest.raises(ValueError,match="^invalid_local_return_history$"):
        validate_local_return_history(history,run_id="foreign")
    with pytest.raises(ValueError,match=CONFLICT):
        validate_local_return_evidence({"version":"local_return_evidence_v1","sample":sample,
            "unavailable_reasons":[]},**arguments)
