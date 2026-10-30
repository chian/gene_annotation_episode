# Workload B numerical ports

Implemented against 362 PLAN_001 and CONTRACT_ADDENDUM_001/002/003, consuming
366's closed inputs. These are supplied-data functions with no I/O, native
imports, model calls, resource choices, episode actions or credit behavior.

```python
# gene_annotation_episode.rna_structure_comparison_calculations
calculate_rna_site_changes(sheet: dict, *, comparison_id: str) -> dict
calculate_rna_pair_changes(sheet: dict, *, comparison_id: str) -> dict
qualify_rna_energy_comparison(baseline: dict | None, variant: dict | None, *,
    request: dict, baseline_software: dict | None,
    variant_software: dict | None) -> dict
calculate_rna_energy_comparison(sheet: dict, *, comparison_id: str) -> dict | None
calculate_rna_comparison_components(sheet: dict) -> dict

# gene_annotation_episode.rna_structure_scan_calculations
calculate_rna_scan_components(sheet: dict, *, pairwise_components: dict) -> dict | None
```

Returns are exactly the accepted shapes: site `{all_site_rows,components,issues}`;
pair `{all_pair_rows,components,pairing_change_state,issues}`; qualifier the
EnergyComparison.compatibility object; energy EnergyComparison or None when
unrequested; scan PopulatedScan or None for pairwise; composition the complete
ComparisonComponents. Original dictionaries are not changed. Malformed closed
inputs raise ValueError; scientifically unavailable valid inputs produce typed
unavailable cells and retained source facts.

The scan input dictionary has all and only the selected comparison IDs. It
consumes complete PopulatedComparison records and never chooses/recalculates
pairwise inputs. Public scan validates the assembled representation through A.
The composition port validates inputs and its final output with A; A imports
neither calculation module. Publication remains responsible for checking the
supplied result against a fresh deterministic calculation on the same sheet.

All requested pair metrics and all metrics for each retained site selection are
present as cells, including unavailable cells. Every explicitly requested energy
comparison has all seven energy cells. Requested scan energy has all aggregate
SCAN_ENERGY_METRICS and individual member rank cells. Unrequested energy has no
implicit selection. Requested-energy scans retain nonnull typed energy/delta/
rank cells for missing or failed members; an unrequested scan uses null fields.
The baseline's delta is exactly zero only for a qualified baseline; otherwise it
is explicitly unavailable. Alias rows copy their canonical values without adding
population weight. Members remain in the parent's declared order.

Resolved selections are consumed exactly as retained. An invalid selection's
empty indices and invalid_site_selection issue never become measured zero. A
valid empty selection has zero counts and unavailable zero-denominator fractions.
Global topology/map failures retain requested/coverage facts while biological
change counts/fractions remain unavailable. Known model differences also remain
qualifications in topology-only comparisons, without requesting an energy.

The population ID is `rna_comparison_population:` plus the canonical SHA256 of
the input-sheet digest, calculator version, comparison ID, selection ID and scan
ID (nullable where inapplicable). It identifies retained membership and choices,
not a new execution. Input paths are real RFC6901 pointers into ComparisonSheet.
Native uncertainty and other retained unused fields are listed separately.

Energy ordering, normalization, difference, tolerance and rank use Fraction of
the saved numeric values; derived numbers round to binary64 once. Exact ties
remain exact even if distinct subnormal ratios round to the same displayed
number. Overflow makes that derived cell unavailable; raw values and exact ranks
can remain usable. Generated arrays qualify only under the accepted exact pinned
profile. Original unavailable array records remain unchanged.

For exactly tied normalized minima, addendum003's first declared minimum carries
its original numerator/length, and every tied input path is retained. No carrier
member or structure is implicitly returned. The four added scan metrics all use
the same qualified R, including the baseline. A valid baseline-only R is legal;
its zero-variant coverage fraction is unavailable.

Test data builders are in fixture_helpers.py here, imported with importlib using
the hyphenated packet name. f.pair() and f.scan() construct explicitly invented
input fixtures. FILLED_EXAMPLES_001.json retains all eight full input/output
examples. Retained357 source packets are separate and documented under the
dedicated test-fixture directory. These fixtures do not establish Store authority
or a complete selected-tool/episode result path.
