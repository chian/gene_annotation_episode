# Draft categorical route withdrawal

This is an additive implementation/verification note. It does not replace the
preserved publications, research, user feedback or scoring proposals. No new
scoring policy is adopted. The accounting remains ten evidence axes and zero
completed scoring sheets.

## Changes

- `gene_annotation_episode/evidence_axis_scoring.py` no longer executes the
  generic ordinal point schedule. A105/A106/A111 assurance and exclusion
  ladders, A108 organism-plausibility/conflict grades and A110 chemical-account/
  conflict grades return `status: unavailable`, reason
  `categorical_scoring_route_withdrawn`, `score: null` and `score_bounds: null`.
  Non-HGT categorical grade mappings have the same withdrawal. Top-level
  `withdrawn_routes` identifies withdrawn routes even when no evidence units
  were supplied. Met, failed and unknown conditions cannot reinstate them.
- Native identity, logarithm and count-ratio calculations retain their inputs,
  units, bounds, uncertainty, deduplication and conflict handling. The explicitly
  justified HGT-environment explanation grade remains available, separately
  from native phylogenetic statistics. This does not prohibit all judgment or
  adopt a replacement sum, product, weight or annotation policy.
- `evidence_axis_contracts.py` documents the distinction between reading a
  historical descriptor and authorizing its execution. Historical schemas and
  source entries remain readable without alteration.
- `scientific_process_library.py` projects evidence-axis `process.entry`
  lookups into a limited instructional view. It renders existing descriptions,
  measurement names, scientific method requirements and comparison limits as
  text, without rubric cells, grading levels, categorical criteria, source
  case records or reader bindings. It states that investigation starts from
  supplied sequence/file/snippets and does not require a candidate annotation
  or a searchable name. `resolve()`, source provenance and frozen entry bytes
  remain exact. The raw v1 schema has no separately reviewed prompt body; the
  view explicitly reports `limited_existing_measurement_guidance`.
- `scientific_process_episodes.py` uses that same view in child decision
  context. It no longer puts the detached draft `axis_judgment_contract` into
  context. The parent's actual typed return contract, selection, scope,
  assignment, tools and thought-pattern guidance remain unchanged.
- `decision_context.py` supplies `instructional_model_context`, a pure
  presentation-copy projection for raw/partial axis entries in lookup replies,
  earlier outcomes and restored exchanges. It is also applied in
  `model_snapshot`. The coordinator owns the runtime dispatch calls. Projection
  must occur before frame revision hashing, including when a saved snapshot
  is used to construct a new delivery; prior recorded requests stay unchanged.

## Verification

Final focused command:

```text
.venv/bin/python -m pytest -q tests/test_evidence_axis_instruction_boundary.py tests/test_evidence_axis_scoring.py tests/test_experimental_evidence_axis_scoring.py tests/test_evidence_axis_scoring_A101_A104.py tests/test_evidence_axis_contracts.py tests/test_decision_context.py
81 passed in 17.61s
```

This verifies withdrawal for complete/partial/missing categorical conditions,
native arithmetic and bounds, the permitted HGT judgment, real retained entry
bytes through freeze/resolve/lookup, actual child construction with a synthetic
assignment, unchanged parent form, historical presentation-copy isolation and
bootstrap/update frame identity. The draft publication has no assembled
`index.json`; these tests construct only a temporary explicitly synthetic index
around the original unmodified A-entry bytes and one original P entry. They do
not create a new publication or claim a completed library.

Final broader command:

```text
.venv/bin/python -m pytest -q tests/test_evidence_axis_instruction_boundary.py tests/test_scientific_process_library.py tests/test_scientific_process_episodes.py tests/test_scientific_support_library.py tests/test_native_evidence_axes_A101_A104.py
2 failed, 103 passed in 10.53s
```

The two remaining observed failures are in `test_scientific_process_episodes.py`:

- `test_mother_report_resolver_honors_process_metadata_and_validates_result_bodies`
  fails at `binding.validate_report(...)`: the test's legacy v2 selection does
  not match the returned-fact schema requiring `scientific_process_selection_v3`.
- `test_setup_freezes_descriptor_without_executable_services_and_reopens_original`
  fails in tool-information preparation with
  `scientific_tool_resource_kind_required:fixture.inspect`.

The failed report-schema and tool-resource paths, and these tests, were not
edited by this workload. Their behavior was not tested against pre-edit source,
so this note does not establish when those failures originated. The test groups
overlap and their counts must not be added as unique coverage.

No model calls, scientific run, external job, historical-run repricing or
publication/research-file rewrite was performed. The full TASK/STEERING
presentation migration, reviewed full investigation prompts, numerical component
sheet design, readers for those sheets and production annotation-credit wiring
are not established by this withdrawal repair.
