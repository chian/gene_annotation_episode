# D candidate delivery, 2026-10-25

The independent D extractor and its saved-contract facades are implemented in the assigned candidate files. The final D test run passed **54 tests in 5.48 seconds**. The real D → N native reader/sheet builder → C calculator boundary also passed on retained, explicitly synthetic inputs. This is deterministic candidate verification; production deployment, authenticated Data acquisition, live ComparativeSystems execution, and episode communication are not claimed.

Only D's two modules, test module and fixture directory were written under candidate. Production-root files, the frozen185 contracts, N/C/P code and the shared115-definition schema were not changed by D. All logs and generated evidence are outside candidate in this directory. No live job was submitted, stopped or restarted.

The exact ports are:

```python
extract_comparative_systems_data_inputs(qualified_inputs: tuple[dict, ...], *,
    artifact_bytes: dict[str, bytes], selection: dict) -> dict
validate_data_population_selection(value: object) -> dict
validate_supplied_record_sets(value: object) -> dict
```

Shapes come from N's actual `bvbrc_comparative_systems_handoff_contracts` data-only module and its unchanged packaged shared schema. D reuses the existing Data encoder/reader to check saved preparation and native-byte/parsed-value correspondence. It does not import N/C implementations for shapes or read verification assets at runtime. Saved facades validate IDs, row/cell locations, normalized values, counts, references and completeness relationships without repeating extraction or scientific calculation.

| Delivered file | SHA256 |
| --- | --- |
| candidate/gene_annotation_episode/bvbrc_comparative_systems_data_inputs.py | b16256d1bb8395efc69757e92306eff86ce2ddd3d17bb657dafe7e5d89153994 |
| candidate/gene_annotation_episode/bvbrc_comparative_systems_data_contracts.py | a008c01d98b7083dd0c966be25ee6b3ee20a6b44442c2cddf588d450853a244d |
| candidate/tests/test_bvbrc_comparative_systems_data_inputs.py | d60ffe4af37bf71b74459015874b0f7e315e23b3ddaad0af86e47ea7d67e2f51 |

`SOURCE_HASHES_001.json` supplies all owned fixture hashes, the authoritative-goal hash, shared-helper/schema hashes and numerical-artifact hashes. The shared schema remains SHA256 `b1310c2f3c7a464191f8c9eb5918d516ed2e6dd13f49bec024a2e9a8bde159f8`.

`COMMANDS_AND_RESULTS_001.json` records exact terminal commands, working directories, exit codes and log paths. All tests use the production-root `.venv/bin/python`, candidate `PYTHONPATH`, disabled bytecode writes, and evidence-local pytest caches/temporary directories. Failures remain retained: attempts001 and003 each had two failures; attempts002,004 and005 passed at their then-current scope. The first numerical evidence run passed D/N/C arithmetic assertions but failed evidence serialization on an incorrect component-key lookup; its traceback remains, and attempt002 passed after correcting that evidence script. No failed run was erased.

The final test command was:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186/candidate /home/chia/repos/gene_annotation_episode/.venv/bin/python -m pytest -q tests/test_bvbrc_comparative_systems_data_inputs.py -o cache_dir=/home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186/evidence_d/pytest-cache --basetemp=/home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186/evidence_d/pytest_attempt_005 > /home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186/evidence_d/pytest_attempt_005.log 2>&1
```

The working directory is the candidate directory. Exit code is 0; the retained log reports 54 passed. The numerical command and its exact result are recorded in `COMMANDS_AND_RESULTS_001.json` and `numerical_example_attempt_002.log`; the reproducible script is `fill_numerical_example_001.py`.

`FILLED_SUPPLIED_RECORD_SETS_001.json` contains D's full output. `FILLED_SHEET_COMPONENTS_001.json` contains the real N-produced sheet and C-produced components, and `NUMERICAL_RESULT_001.json` records their numerical meaning. The synthetic Data response contains five native unique records, three explicitly selected genomes, three ECs and four distinct genome–EC pairs. D reports native broad-query total 5, retained occurrences 5, locally included unique records 5, and valid included unique records 5. C computes 4/(3×3)×100 = 44.44444444444444% for `later_pathway_genomes`; the native 2-genome/2-EC population retains 3/(2×2)×100 = 75% under `pathway_native_genomes`. D does not compute or replace these scientific ratios.

The test with explicit local PATRIC filtering retains all five broad-query rows while including only two exact-case PATRIC records. Missing/invalid filter values remain undetermined. Raw occurrence counts include invalid, excluded and repeated occurrences; local included counts deduplicate known included record IDs; distinct valid-member counts exclude invalid associations and conflicts. These retained-subset counts may remain available with partial-population qualifications. Native broader totals are never summed across pages.

Verification covers exact byte/value/preparation binding; changed source/hash/core/page/query/fields/sort; exact empty zero versus failed/missing/partial data; invalid totals; unknown/false numFoundExact; partialResults; incomplete body; HTTP failure; gaps, repeats, overlaps and conflicting unique keys; cross-page access-scope mismatch; unknown original group expansion; exact genome strings; non-CDS feature occurrences; shared sequence hashes; invalid/missing/negative lengths; PLFam/PGFam separation; multiple pathway maps; independent subsystem role-ID/name arrays; preserved complex/unselected raw fields and numeric lexemes; and tampered saved counts, categories, pointers and completeness labels. Network clients, sockets, Store reads, model calls, subprocesses and file opens are forbidden during the purity test. Saved facade validation additionally runs with extraction/native parsing forbidden. Inputs remain unchanged.

The complete original goal, applicable AGENTS, accepted185 documents in additive precedence, shared definitions/examples, existing Data host/preparation/parser/publication/field consumers, BLAST extraction separation, and the relevant actual N/C consumers were inspected. After substantial source examination and at the end of D work, the objective and entire DESIGN PRINCIPLES block were reread directly and verbatim from the authoritative attachment, followed by the exact D contracts. `COMMANDS_AND_RESULTS_001.json` records the final reset source and hash.

Unfinished I/P dependencies remain explicit:

- I must authenticate selected sources through the actual `BVBRCDataHost.read` boundary and materialize the already retained bytes. D's synthetic wrappers contain clearly labelled hypothetical true flags; D cannot prove possession from JSON. Fabricated/self-authored wrappers must be rejected by I's host integration, including the original selected Data publication and receiver scope.
- P must call D only for its selected dependencies, pass the output to N, preserve native-only requests, and materialize explicit reference membership from delivered source cells/context. Subsystem reference `role_id` arrays remain valid native cell atoms; `association.identifiers.role_id` is null for multivalued cells. Role names are never zipped to IDs. D returns no fabricated reference-membership list.
- Root confirmed that no native immutable-snapshot attestation or original remote-task Data/group proof format is currently bound. D preserves the requested selection but demotes derived `original_execution_snapshot` relationships to `unverified` with `data_input_binding_mismatch`/`original_genome_population` requirements. Caller snapshot labels never yield `proven_same_snapshot`. Exact multi-page coverage remains snapshot-consistency unknown. A complete single exact response supports its observed query population only. No shared schema change was needed.
- A supplied release label is retained selection metadata, not native immutable-release evidence. Unknown reference release remains qualified. Original group expansion, deployed versions/releases, actual live response availability, provider/host binding and typed episode delivery remain I/P/root verification work. This delivery does not establish biological absence, biochemical completion or a complete deployed scientific tool.
