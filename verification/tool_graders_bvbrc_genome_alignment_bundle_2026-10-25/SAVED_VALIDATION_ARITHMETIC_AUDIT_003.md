# Strict saved replay remains blocked by existing validation arithmetic

E's three saved projection APIs call `validate_genome_alignment_sheet`, as
accepted E001 requires. That D function calls
`validate_genome_alignment_components`, whose `COMPONENT_VALIDATORS` dispatch
uses the existing A/B/XMFA component validators. Those validators perform
scientific arithmetic in addition to checking stored structure. E itself copies
selected stored values; bypassing or weakening the D validator is not an
authorized repair.

`REPLAY_UNION_BARRIER_001.txt` retains the first exact failure stack.
`REPLAY_ARITHMETIC_TRACE_002.json` records actual calls during one saved E
projection of a real seven-family D sheet. Source and C association witnesses in
that fixture are explicitly synthetic. This trace is not a native run or a
claim of authenticated service provenance.

The strictly failing regression is
`test_strict_saved_boundary_never_recomputes_union_coverage_or_entropy` in the
owned projection test file, parameterized over all three public E saved APIs.
It is neither skipped nor marked expected-failure. It forbids the public
parsers/calculators/C/source-binding calls, the four scientific interval helpers
at each imported alias, and `math.log2`. Root explicitly owns the bounded
D/native structural-validation correction; E does not edit those files.

## Reached scientific helpers and inline computations

Line numbers below describe the source inspected before that root repair.

| Existing source/function | Recomputed scientific content |
| --- | --- |
| `mauve_v4_calculation_contracts.validate_mauve_v4_components`, lines 175, 232 | Selected interval lengths and category/population totals. |
| Same, lines 260–287 | Placement union, union length, placement sum, multiplicity, excess, complement intervals/length. |
| `mauve_v4_calculation_contracts._cell`, lines 124–133 | Fraction division `n / d`, including identity and coverage. |
| `mauve_backbone_contracts._coverage_counts`, lines 465–481 | Union, lengths, multiplicity and excess. |
| `mauve_backbone_contracts.validate_mauve_backbone_components`, lines 490–550 | Selected member counts, span lengths, coverage/complement arithmetic. |
| `mauve_backbone_contracts.validate_mauve_bbcols_components`, lines 595–627 | Canonical union, placement-width sum, union length, excess and fraction inputs. |
| `mauve_backbone_contracts._cell`, lines 407–420 | Stored fraction numerator/denominator division. |
| `xmfa_calculation_contracts.validate_xmfa_alignment_components`, lines 335–422 | Site/category sums, canonical-majority numerator, pair category totals and entropy. The trace observed **204 `math.log2` calls** at line 394. |
| `xmfa_calculation_contracts.validate_xmfa_coverage_components`, lines 463–487 | Placement unions, lengths, multiplicity/excess, complement. |
| Same, original-coverage branch, lines 501–525 | Canonical original union and its length; fraction relationships. This branch is additionally covered by the strict regression's synthetic feature-map fixture. |
| `xmfa_calculation_contracts._cell`, lines 168–182 | Fraction division for identity, majority, source coverage and original coverage. |

The four shared scientific helpers are
`xmfa_calculation_contracts.union_intervals`, `interval_length`,
`multiplicity_bases`, and `complement_intervals`; A and B import aliases. The
XMFA `_union` helper calls `union_intervals` to normalize the stored interval
list. The similarly named D `_union` only deduplicates reports and is not a
scientific interval operation.

D's own `_bbcols_links` checks saved contributors, endpoint relationships,
document/member references and bounds without calling a scientific interval
union. D's native-source snapshot validator checks stored identities and
components; it does not call `validate_xmfa_bindings_for_document`. The broader
existing component validation is the actual observed failure path. Inline
division is not intercepted by the helper monkeypatch; the source audit keeps
that additional obligation visible.

Native format/token/coordinate validation, finite numerical types, stored
reference/selection correspondence, interval endpoint ordering and identifier
bijections remain necessary structural checks. Removing scientific
recomputation must preserve these checks and exact sheet/components equality.

Until the root repair and strict regression pass, neither E nor downstream F
can claim the accepted saved-only boundary is verified. The narrower no-public-
calculator/no-parser/no-I/O tests passing does not erase this limitation.
