"""Support-custody regressions using explicitly synthetic control populations."""


import pytest

from gene_annotation_episode.episodic_workflow.root.library.fluorescence_event_contracts import canonical, control_comparison_files
from test_fluorescence_event_calculations import _control_sheet


@pytest.mark.parametrize("prepared,expected_count", [(False, 7), (True, 8)])
def test_comparison_files_preserve_exact_distinct_field_locations(prepared, expected_count):
    sheet = _control_sheet(prepared_control=prepared)
    before = canonical(sheet)
    files = control_comparison_files(sheet, control_key="pair")
    assert len(files) == expected_count
    assert len({row["pointer"] for row in files}) == expected_count
    for row in files:
        value = sheet
        for token in row["pointer"].removeprefix("sheet:/").split("/"):
            value = value[int(token)] if isinstance(value, list) else value[token]
        assert row["file"] == value
    files[0]["file"]["format"] = "changed detached copy"
    assert canonical(sheet) == before


