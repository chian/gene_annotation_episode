"""The literal test retriever selects only actual callable registry contracts.

These checks establish map custody and construction operands, not biological
relevance or configured-model retrieval quality.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools


def actual_catalog(tmp_path):
    with Store(tmp_path / "state") as store:
        return build_tools(store).catalog()


def test_full_actual_map_round_trips_without_tool_bundles(tmp_path):
    actual = actual_catalog(tmp_path)
    directory = tmp_path / "tools"
    library = ScientificToolLibrary.freeze(directory, catalog=actual)
    expected = [{"name": name, **entry} for name, entry in sorted(actual.items())]
    assert library.catalog() == expected
    assert ScientificToolLibrary(directory).catalog() == expected
    assert ScientificToolLibrary(directory).as_record() == library.as_record()
    assert len(library.catalog()) == len(actual)
    # A returned copy cannot alter any subsequent child's actual contract.
    copy = library.catalog()
    copy[0]["input_schema"] = {"type": "null"}
    assert library.catalog() == expected


def test_investigations_retrieve_different_multi_tool_sets_from_actual_map(tmp_path):
    actual = actual_catalog(tmp_path)
    library = ScientificToolLibrary.freeze(tmp_path / "tools", catalog=actual)
    composition = library.retrieve("composition translation codes")
    archives = library.retrieve("archive inventoried")
    assert {"sequence.inspect", "translation.codes"} <= set(composition["tools"])
    assert {"source.archive.members", "source.archive.extract"} <= set(archives["tools"])
    assert len(composition["tools"]) > 1 and len(archives["tools"]) > 1
    assert composition["tools"] != archives["tools"]
    for result in (composition, archives):
        assert len(result["tools"]) == len(set(result["tools"]))
        assert set(result["tools"]) <= actual.keys()
        assert result["catalog"] == [
            {"name": name, **actual[name]} for name in result["tools"]]
        assert library.resolve(result["tools"], actual) == result["catalog"]
    assert not {"sequence.inspect", "translation.codes"}.intersection(archives["tools"])
    assert library.retrieve("zzunmatchedzz") == {
        "investigation": "zzunmatchedzz", "tools": [], "catalog": []}


@pytest.mark.parametrize("names", [["invented.annotation.tool"],
    ["state.query", "state.query"], "state.query", [None]])
def test_resolution_rejects_invented_or_malformed_tool_selections(tmp_path, names):
    library = ScientificToolLibrary.freeze(tmp_path / "tools", catalog=actual_catalog(tmp_path))
    with pytest.raises(ValueError):
        library.resolve(names)


@pytest.mark.parametrize("drift", ["missing", "schema", "description"])
def test_selected_actual_contract_must_remain_available_and_exact(tmp_path, drift):
    actual = actual_catalog(tmp_path)
    library = ScientificToolLibrary.freeze(tmp_path / "tools", catalog=actual)
    changed = deepcopy(actual)
    if drift == "missing":
        del changed["state.query"]
    elif drift == "schema":
        changed["state.query"]["input_schema"] = {"type": "null"}
    else:
        changed["state.query"]["description"] += " A changed instruction."
    with pytest.raises(ValueError, match="scientific_tool_contract_changed"):
        library.resolve(["state.query"], changed)
    assert library.resolve(["state.query"], actual) == [
        {"name": "state.query", **actual["state.query"]}]


def test_frozen_actual_map_rejects_replacement_and_file_drift(tmp_path):
    actual = actual_catalog(tmp_path)
    directory = tmp_path / "tools"
    library = ScientificToolLibrary.freeze(directory, catalog=actual)
    changed = deepcopy(actual)
    del changed["state.query"]
    with pytest.raises(ValueError, match="scientific_tool_catalog_changed"):
        ScientificToolLibrary.freeze(directory, catalog=changed)
    path = directory / "index.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="scientific_tool_snapshot_changed"):
        library.retrieve("translation")
    with pytest.raises(ValueError, match="scientific_tool_snapshot_changed"):
        ScientificToolLibrary(directory)
