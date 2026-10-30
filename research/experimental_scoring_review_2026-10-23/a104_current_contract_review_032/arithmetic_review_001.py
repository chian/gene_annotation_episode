"""Bounded additive verification of A104 proposal004 and checker005.

This loads the unchanged synthetic checker and compares its complete output
with its saved receipt. It repairs two fixture helpers only: known-zero
product absorption and a resolved clade crossing obscured by an unrelated
polytomy. It is not a biological reader or general phylogenetic implementation.
Run from any working directory; JSON is written to stdout, never to old files.
"""

from contextlib import redirect_stdout
from fractions import Fraction as Q
from hashlib import sha256
from io import StringIO
from pathlib import Path
import json
import runpy


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "a104_clade_support_completion_025"
original_stdout = StringIO()
with redirect_stdout(original_stdout):
    old = runpy.run_path(str(SOURCE / "arithmetic_checks_005.py"))
fresh_original = json.loads(original_stdout.getvalue())
saved_original = json.loads((SOURCE / "arithmetic_results_005.json").read_text())
assert fresh_original == saved_original


def contribution_product(factors):
    """Research fixture factors: exact [0,1] values or missing None.

    Missing cells stay missing. A known zero identifies the product without
    estimating any missing factor. This helper supplies no uncertainty model.
    """
    assert set(factors) == {"C", "F", "J", "O"}
    known = [v for v in factors.values() if v is not None]
    assert all(Q(0) <= v <= Q(1) for v in known)
    missing = [k for k, v in factors.items() if v is None]
    zeros = [k for k, v in factors.items() if v == 0]
    if zeros:
        point = Q(0)
    elif missing:
        point = None
    else:
        point = Q(1)
        for value in known:
            point *= value
    return dict(point=point, factors=dict(factors), missing=missing,
                known_zero_factors=zeros)


def fixture_membership_with_cluster_check(tree, crown):
    """Repair only the rooted, complete-label unresolved-membership branch.

    A crown incompatible with an already resolved descendant cluster cannot
    become monophyletic by resolving an unrelated polytomy. Other old fixture
    conventions and limitations remain unchanged.
    """
    initial = old["membership"](tree, crown)
    if initial[2] != "unresolved_membership":
        return initial
    backbone, _ = old["prune_query"](tree)
    crown = frozenset(crown)
    assert crown <= old["leaves"](backbone)
    nodes = old["index"](backbone)[0]
    for node in nodes.values():
        cluster = old["leaves"](node)
        if crown & cluster and crown - cluster and cluster - crown:
            return [Q(0), Q(0), "resolved_nonmonophyly"]
    return initial


# Reproduce the old score() failure using its actual tree/function operands.
stem = old["score"](old["trees"][2], old["organism"], ["a", "b"],
                    {"a": ["f"]}, old["taxa"])
assert stem["a"] is None
stem_factors = dict(C=stem["function"]["C"],
                    F=stem["concordance"]["supported"],
                    J=stem["membership"][0], O=stem["locality"]["O"])
stem_corrected = contribution_product(stem_factors)
assert stem_factors == dict(C=Q(1, 2), F=Q(3, 4), J=Q(0), O=None)
assert stem_corrected["point"] == 0
assert stem_corrected["factors"]["O"] is None
assert stem_corrected["missing"] == ["O"]

# Each factor can identify zero while every other factor remains unknown.
zero_cases = {}
for factor in ("C", "F", "J", "O"):
    inputs = dict.fromkeys(("C", "F", "J", "O"))
    inputs[factor] = Q(0)
    before = dict(inputs)
    value = contribution_product(inputs)
    assert value["point"] == 0
    assert len(value["missing"]) == 3
    assert inputs == before and value["factors"] == before
    zero_cases[factor] = value
positive = contribution_product(dict(C=Q(1), F=Q(3, 4), J=Q(1), O=Q(1)))
missing_nonzero = contribution_product(dict(C=Q(1), F=Q(3, 4), J=Q(1), O=None))
assert positive["point"] == Q(3, 4)
assert missing_nonzero["point"] is None

# The resolved (a,c) cluster crosses crown {a,b}; (d,e,f) is unrelated.
polytomy_text = "((((q:.1,a:.1):.1,c:.2):.1,b:.4):.1,(d:.1,e:.1,f:.1):.1)root;"
polytomy_tree = old["parse"](polytomy_text)
polytomy_old = old["membership"](polytomy_tree, ["a", "b"])
polytomy_fixed = fixture_membership_with_cluster_check(polytomy_tree, ["a", "b"])
assert polytomy_old == [0, 1, "unresolved_membership"]
assert polytomy_fixed == [0, 0, "resolved_nonmonophyly"]
resolved_trees = old["refinements"](polytomy_tree)
refinement_memberships = [old["membership"](t, ["a", "b"]) for t in resolved_trees]
assert len(refinement_memberships) == 3
assert all(j == [0, 0, "resolved_nonmonophyly"] for j in refinement_memberships)
base_memberships = [fixture_membership_with_cluster_check(t, ["a", "b"])
                    for t in old["trees"]]
assert base_memberships == [r["membership"] for r in old["rows"]]
boundary_fixed = fixture_membership_with_cluster_check(old["boundary"], ["a", "b"])
assert boundary_fixed == [0, 1, "boundary"]

# Algebra only: hypothetical supplied joint draws, not biological observations
# or a probability assigned to contradictory source interpretations.
coupled_factors = [(Q(1, 2), Q(1), Q(0)), (Q(1, 2), Q(0), Q(1))]
correct_joint = sum(w * c * f for w, c, f in coupled_factors)
incorrect_factoring = (sum(w * c for w, c, f in coupled_factors)
                       * sum(w * f for w, c, f in coupled_factors))
assert correct_joint == 0 and incorrect_factoring == Q(1, 4)


def export(value):
    if isinstance(value, Q):
        return {"exact": str(value), "decimal": float(value)}
    if isinstance(value, dict):
        return {k: export(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [export(v) for v in value]
    return value


receipt = dict(
    status="all bounded assertions passed",
    original_checker=dict(
        file="arithmetic_checks_005.py",
        sha256=sha256((SOURCE / "arithmetic_checks_005.py").read_bytes()).hexdigest(),
        complete_fresh_output_matches_saved_receipt=True,
        saved_receipt_sha256=sha256((SOURCE / "arithmetic_results_005.json").read_bytes()).hexdigest(),
        original_grid_checks=fresh_original["range_grid_checks"],
        original_base_region=fresh_original["base_region"],
        original_far_region=fresh_original["outlier_region"],
        original_joint_candidate=fresh_original["candidate"]["with_constant_required_region"],
    ),
    zero_absorption=dict(original_stem_score=stem["a"],
                         corrected_stem=stem_corrected,
                         each_factor_zero=zero_cases,
                         positive_control=positive,
                         missing_without_zero=missing_nonzero),
    unrelated_polytomy=dict(tree=polytomy_text, crown=["a", "b"],
                            old_membership=polytomy_old,
                            corrected_membership=polytomy_fixed,
                            exact_allowed_binary_refinement_count=len(resolved_trees),
                            refinement_memberships=refinement_memberships,
                            unchanged_base_memberships=base_memberships,
                            unchanged_boundary=boundary_fixed),
    handoff_factoring=dict(supplied_algebraic_draws=coupled_factors,
                           within_draw_result=correct_joint,
                           product_of_factor_means=incorrect_factoring),
    limits=[
        "Synthetic finite fixtures only; original files remain unchanged.",
        "No primary paper or retained paper-specific source packet opened.",
        "No source-reader, native tree analysis, arbitrary-tree completeness, or invalid-input validation claim.",
        "The source checker's published ratios are checked arithmetically, not reverified against papers.",
        "No empirical calibration, production scoring, axis-completion, or goal-completion claim.",
    ],
)
print(json.dumps(export(receipt), indent=2))
