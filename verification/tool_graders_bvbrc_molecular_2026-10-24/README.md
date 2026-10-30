D4 molecular association extraction, 2026-10-24

The owned implementation is `gene_annotation_episode/bvbrc_data_molecular.py`;
the focused checks are `tests/test_bvbrc_data_molecular.py`. The extractor accepts
only supplied DataSheets and exact supplied metadata, produces the frozen
MolecularSheet with correction002 supplied locators, and performs no I/O.

The retained native example preserves these measured pairs:

| Result | Experiment | Bioset | log2_fc | z_score |
| --- | --- | --- | ---: | ---: |
| 00000125-8a72-4eea-aad0-d58d4fdb772c | 65769 | 53111326 | -0.132 | -0.544 |
| 00000317-5d60-4e06-9c35-c42e53fd5ae3 | 30087 | 57692532 | -0.129 | -0.556 |

Counts, FPKM, TPM, p-value and other_value are missing in both native examples.
Units, replication and correction methods remain unknown. The second bioset's
duration is exactly the native empty string. Experiment treatment arrays remain
aggregate arrays; no sample or replicate association is created from their order.

`INPUT_FIXTURES.json` labels independently constructed DataSheets from retained
native bytes separately from wholly synthetic inputs. Their prepared/population
identities do not assert a historical v2 request or host admission.
`FILLED_EXAMPLES.json` contains complete extractor outputs for that native case,
synthetic seven-field measurements, supplied null/empty metadata and conflicting
supplied unit/design records. `HASHES.json` identifies the exact evidence and
implementation versions used. `TEST_RESULT.txt` records the actual 54-test result.

Run the reproducible artifact checks from the repository root:

```text
.venv/bin/python verification/tool_graders_bvbrc_molecular_2026-10-24/verify.py
```

No network, jobs, live acquisition or complete episode path was executed here.
The host must separately prove source receipt/custody and exact supplied-source
content, bind the selected resource child's operation, publish the retained
sheet, and deliver the selected facts and native values to the actual receiver.
The pure extractor checks local IDs and references; it cannot prove those host
facts. No expression statistic, literature grader or W05 formula was added.
