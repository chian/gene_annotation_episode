# Commands and retained attempts

Source reads used the immutable objective, AGENTS.md, contract027, design documents, native contract and consumers, installed referencing/jsonschema code, and retained415/416 records.

A source-diff attempt using `git diff -- gene_annotation_episode/native_protein_structure_contracts.py` returned129 because this workspace is not a Git repository. No files changed; the prechange module supports a direct diff.

The pytest launcher is copied from416 with the test selection and both prechange module inputs changed for417. The profile launcher and diagnostic are exact byte copies of415; their own `__file__` places new results in417.

The initial `rg --files gene_annotation_episode tests scripts` read returned2 because this checkout has no `scripts` directory; the relevant files under the two real directories were still listed.

Executed attempts, all successful and all retained:

- `run_bounded.py check001`:133tests,54.30s;20GiB RAM,4GiB scratch,zero swap,no wall limit.
- `run_profile_bounded.py profile001`:same unchanged415harness and closed410/check007input;actual admission accepted.
- `run_analysis_bounded.py analysis001`:saved-output comparison only under the same limits;all equality/preservation/count assertions passed.
