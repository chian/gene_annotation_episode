# D1 pure preparation grading — workload271

The two ports in `gene_annotation_episode/native_hmmer_preparation_worker.py`
compose the existing A1/B1/E1/S1/H1/F1 readers and calculators. The exact authority
is [261/D1](../tool_graders_hmmer_preparation_2026-10-26_261/GRADING_DISPATCH_CONTRACT_001.md).
This work owns no capture, artifact publication, selector, episode, annotation
credit, resource decision, or native execution. The original 308-row assignment
is unchanged; successful D1 composition is not full-tool completion.

```python
grade_hmmer_preparation(*, operation, inputs, outputs, formats, metadata,
                        parameters, native_abi=None)
recalculate_hmmer_preparation(sheet, *, parameters)
```

The first port takes supplied byte payloads and explicit original declarations.
The second takes a saved numerical sheet and calls only its calculator. Neither
opens files, contacts services, invokes native software, accesses Store, calls a
model, or creates observations. Original settings and requested parameters remain
separate from calculators' resolved parameters. No native or statistical default
is inserted into the original operation.

[FIELDS.md](FIELDS.md) documents the envelope, dispatch, errors, and parameter
boundaries. Scientific field meanings remain those of the existing component
implementations; D1 adds no scientific scoring formula.

Final verification is [check004/receipt.json](check004/receipt.json): **135 passed
in 5.80 s**, with source hashes unchanged during the run. The command was
`.venv/bin/python verification/tool_graders_hmmer_preparation_grading_2026-10-26_271/run_verification.py check004`.
The existing `local_jobs` policy enforced 20 GiB RAM, 4 GiB scratch, and no wall
cap. This workload launched pytest and artifact-generation Python processes;
it launched no native scientific software. Its scientific data came from prior
retained actual native executions: all 77 producer267 cases covering all 26
program/mode pairs, four corrected producer270 simulation cases, and the
specified original259 numerical examples. Bundle and receipt digests and staged
input/output bytes are checked in the tests. Mutated negative fixtures are
identified separately in test names and never represented as native measurements.

| Actual example | Checked numerical result | Complete filled envelope |
| --- | --- | --- |
| H1 DNA | Mean match KL = 1.0074921672642938 bits/position; explicit native background and length probability | [H1.json](check004/temporary/test_save_complete_actual_exam0/H1.json) |
| S1 Viterbi259 | Mean = -5.619071923450204 bits across 1,000 original binary64 scores | [S1.json](check004/temporary/test_save_complete_actual_exam0/S1.json) |
| E1 simple consensus | Generated and independently reconstructed sequence = ACDEFGHIKLMN | [E1.json](check004/temporary/test_save_complete_actual_exam0/E1.json) |
| F1 database | 28 source symbols; 314 actual database bytes | [F1.json](check004/temporary/test_save_complete_actual_exam0/F1.json) |
| A1 pressed bundle | 2725 + 165 + 9918 + 3216 = 16024 actual bytes | [A1.json](check004/temporary/test_save_complete_actual_exam0/A1.json) |
| A1 aliases | One unindexed returned model versus two indexed returned models | [Unindexed](check004/temporary/test_save_complete_actual_exam0/A1_alias_unindexed.json), [indexed](check004/temporary/test_save_complete_actual_exam0/A1_alias_indexed.json) |
| B1 build | 3 input sequences, 14 source columns, 12 model positions | [B1.json](check004/temporary/test_save_complete_actual_exam0/B1.json) |
| B1 mask | Inclusive union of 2–4 and 4–6 is 5 columns; fraction 5/14 | [B1_mask.json](check004/temporary/test_save_complete_actual_exam0/B1_mask.json) |

H1 KL is additionally checked by directly exponentiating the retained native
cost tokens and summing p*log2(p/0.25), divided by 12 positions. S1 mean is
additionally checked by unpacking the original retained score bytes and using
`math.fsum(values)/len(values)`. F1 counts use the source FASTA sequence lines and
actual byte length; A1 checks the four independently known native artifact sizes.
The mask test computes the explicit inclusive set union. These are independent
numerical checks, in addition to saved-result consistency tests.

The final suite covers byte/digest/size/identity/ordinal/format validation;
same-byte distinct roles; absent, empty, partial, unsupported, and nonfinite data;
malformed metadata; unknown parameter keys; explicit unsupported ABI; all input
model occurrences; and missing models without fabricated M1 envelopes. It
prohibits file/network/subprocess/Store access during both supplied-byte grading
and saved recalculation, and prohibits native readers during recalculation.
Negative length probability invalidates its dependent quantity while preserving
valid KL. Missing background leaves KL unknown. Empty singlemx resaved alignment
and missing redirected summary retain explicit diagnostics and useful build
quantities.

The old267 hmmsim operations omit resolved false `--fast` and `--tlinear` facts;
D1 preserves those exact operations and S1's qualifications. The four270 native
bundles contain the recorded defaults and yield present score means. See
[the producer handoff](../tool_graders_hmmer_preparation_2026-10-26_261/SIMULATION_SETTINGS_HANDOFF_001.md).
HMMER2/binary M1 decoding remains unsupported; original bytes and artifact facts
survive. Missing ABI does not permit binary decoding. Imported FM decoding uses
only explicit producer metadata; a search ABI is never substituted. Metadata
equality is not custody authentication. E1/H1 may have no calculated model rows
when the model is missing, while their saved sheets retain available output
records and native rows. Component issues are retained with their actual meaning.

`check001`–`check003` are preserved failed development receipts. Their failures
were test assumptions and one shared test-ABI mutation; the final tests copy
caller ABI fixtures. They are not final verification evidence.

For the projection consumer, [modes001/manifest.json](modes001/manifest.json)
indexes 26 complete D1 envelopes, one per exact native program/mode. Generation
used the same bounded local policy, preserved original requested grading
parameters, and made zero native invocations. The four S1 envelopes use current
270 bundles; the other 22 use original267 bundles. The complete retained
envelopes total 13,851,014 bytes; they are not model-facing prompt content.

Worker SHA256: `983b1edd8fdf1bbd081eab85b141d3f35e0162fed7fcbc2e9c8f54189d4ca110`.
Test SHA256: `190d2a6b89c4ef35c7b03683c6142ebf81f913bd1b7d796358a1d7dd76e9f9e1`.
Final receipt SHA256: `2c57b897f2d14c2aa38ec3162d90afb18cbfb02e46cab3f9a42a4800d02f3463`.
The [evidence manifest](SOURCE_AND_EVIDENCE_MANIFEST_001.json) records exact paths,
hashes, retained native sources, and all nine complete filled examples. Root
integration and the parent-requested typed projection remain separate work.
