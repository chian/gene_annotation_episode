"""A malformed explicit native alphabet cannot become an invented default."""
from copy import deepcopy

import pytest

from gene_annotation_episode.blast_pssm_inputs import read_blast_pssm
from gene_annotation_episode.blast_pssm_calculators import calculate_blast_pssm_components


@pytest.mark.parametrize("rows,is_protein", [(26, True), (28, True), (16, False)])
@pytest.mark.parametrize("labels", [
    'rowLabels { "custom" }, ',
    'rowLabels 7, ',
    'rowLabels { "A" }, rowLabels { "C" }, ',
])
def test_invalid_supplied_alphabet_preserves_indexed_matrix(rows, is_protein, labels):
    values = ", ".join(str(i) for i in range(rows))
    text = (f"Pssm ::= {{ isProtein {'TRUE' if is_protein else 'FALSE'}, "
            f"numRows {rows}, numColumns 1, {labels}"
            f"intermediateData {{ freqRatios {{ {values} }} }} }}")
    sheet = read_blast_pssm(text.encode(), format="scoremat_asn_text",
                           artifact_key="explicit-label-example", source_ref="synthetic-format-counterexample")
    before = deepcopy(sheet)
    result = calculate_blast_pssm_components(sheet)
    matrix, = result["matrices"]
    assert matrix["residue_alphabet"] is None
    assert matrix["alphabet_source"] is None
    assert matrix["matrix_values"]["freqRatios"] == [list(range(rows))]
    assert "row_labels_incompatible" in {issue["code"] for issue in matrix["issues"]}
    assert sheet == before
