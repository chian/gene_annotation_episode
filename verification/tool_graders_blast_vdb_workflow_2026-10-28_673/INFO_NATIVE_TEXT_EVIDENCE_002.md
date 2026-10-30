# Exact retained info text for the wrapping investigation

This is additive evidence for `INFO_WRAPPED_PATH_FINDING_001.md`; that original
finding and the original native/Workflow records remain unchanged.

The new retained-only bounded attempt is
`verification/tool_graders_hmmer_map_verification_2026-10-28_529/check131_vdb_workflow673_info/check131_vdb_workflow673_info_text/`.
Its unit `gene-local-job-93dd14d60946456fb1192a3d60002f87.service` closed
terminal/quiescent rc0. `test_retain_closed_info_native_text` passed in
0.025327591923996806 seconds. Source/dependency/stdlib/binary pins and native
files were unchanged; outside modules and unbound mappings were empty. The
test opened no Store and executed no helper, native parser, or acquisition.

`ORIGINAL_INFO_STDOUT.txt` in that new attempt is a byte-for-byte copy of the
original stdout: 423 bytes, SHA256
`cb65d0f9b71a60a74dcbabb602dcd86cdc29e6b5d65c2d0ec3d7c7235c174e0a`.
`INFO_NATIVE_TEXT.json` retains the original source path, before/after identity,
and the entire text. Its exact escaped UTF-8 text is:

```json
"Database(s): \n/home/chia/repos/gene_annotation_episode/verification/tool_graders_blast_vdb_\nfixture_acquisition_2026-10-28_658/retained/fixture/ERR3487613\nDatabase(s) Full Path: \n/home/chia/repos/gene_annotation_episode/verification/tool_graders_blast_vdb_\nfixture_acquisition_2026-10-28_658/retained/fixture/ERR3487613\n\t20 sequences; 5,000 total bases (unclipped)\n\tLongest sequence: 250 bases\n\tAverage sequence: 250 bases\n"
```

Root assigned upstream formatting-source investigation and a narrow repair
proposal to `/root/vdb_info_wrapping_678`. That owner has this exact retained
stdout location. No new source location or wrapping rule is inferred here;
its independently established source evidence will be an additional record.
