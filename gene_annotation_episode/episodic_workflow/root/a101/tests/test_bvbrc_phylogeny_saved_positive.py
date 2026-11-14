"""One exact original controlled saved-value test; no historical Store claim."""
import sys
import pytest
from .bvbrc_phylogeny_saved_fixture import projection, deepcopy, all_facts, numbers, BRANCHES, SITES, MEMBERS, FUNCTIONS, COMPARISONS, REQUIREMENTS, QUALIFICATIONS, ref, validate_closed_schema, fact_form, FACT_SOURCES, form_with_facts, validate_form, canonical

ORIGINAL_SCIENCE_TARGETS = {'phylogeny_formats': ['parse_newick', 'parse_aligned_fasta', 'parse_relaxed_phylip', 'parse_phyloxml'], 'phylogeny_calculators': ['alignment_components', 'tree_components', 'function_composition', 'compare_unrooted_relationships'], 'bvbrc_gene_tree_inputs': ['extract_gene_tree_sheet'], 'bvbrc_codon_tree_inputs': ['extract_codon_tree_sheet'], 'bvbrc_gene_tree_grader': ['calculate_gene_tree'], 'bvbrc_codon_tree_grader': ['calculate_codon_tree'], 'bvbrc_gene_tree_bundle_adapter': ['consume_bundle'], 'bvbrc_codon_tree_bundle_adapter': ['consume_bundle'], 'bvbrc_phylogeny_bundle_resolution': ['parse_reader'], 'bvbrc_phylogeny_bundle_projection': ['consume_bundle']}

@pytest.fixture(autouse=True)
def no_acquisition_or_scientific_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Saved return attempted acquisition, parsing, calculation or execution")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    # Detect original forbidden scientific entry points even through aliases.
    # No omitted provider is imported to create this execution guard.
    previous = sys.getprofile()
    def guard(frame, event, argument):
        if event == 'call':
            module = frame.f_globals.get('__name__', '').rsplit('.', 1)[-1]
            if frame.f_code.co_name in ORIGINAL_SCIENCE_TARGETS.get(module, ()):
                forbidden()
        if previous is not None:
            previous(frame, event, argument)
    sys.setprofile(guard)
    try:
        yield
    finally:
        sys.setprofile(previous)

def test_all_eight_closed_families_preserve_saved_numbers_and_references():
    body, sheet = projection()
    original = deepcopy((body, sheet))
    facts = all_facts(body, sheet)
    assert numbers(facts) == {"tips": 4, "negative": -.5, "zero": 0, "missing": None}
    assert type(numbers(facts)["tips"]) is int
    assert facts[BRANCHES][0]["branches"][0]["length"] == -.125
    assert facts[SITES][0]["sites"][1]["gap_count"] == 1
    assert facts[MEMBERS][0]["members"][1]["representation"] == "coding_nucleotide"
    assert facts[FUNCTIONS][0]["functions"][0]["fraction_all"] == .5
    assert facts[COMPARISONS][0]["comparisons"][0]["rf"] == 0
    assert facts[REQUIREMENTS][0]["requirements"] == []
    assert facts[QUALIFICATIONS][0]["qualifications"][0]["role_ref"] == ref("role", "raw_tree")
    schema = validate_closed_schema(fact_form(*FACT_SOURCES))
    form = form_with_facts({}, schema, facts)
    assert validate_form(form, schema, lambda *_: True) == form
    assert (body, sheet) == original
    assert "documents" not in canonical(facts) and "sheet_content" not in canonical(facts)
