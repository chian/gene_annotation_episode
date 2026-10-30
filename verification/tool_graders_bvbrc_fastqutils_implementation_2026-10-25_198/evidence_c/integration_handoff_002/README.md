This is an actual execution of the pure FastqUtils provider, parsers, metadata
extractor, sheet builder, calculators, projection and saved validator against the
immutable source copy in `../frozen_001/source`. Inputs are handcrafted synthetic
FASTQ, Hostile JSON and FastQC data. No native producer executable, live BV-BRC
service, authenticated custody or complete episode path was exercised here.

`provider_result.json` is the filled public ProviderResult. It includes all seven
fact families in nine selected fields. `native_documents.json`, `metadata.json`,
`sheet.json`, `calculation_parameters.json`, `calculated_components.json`,
`saved_components.json` and `selected_facts.json` preserve every intermediate.
`NUMERICAL_AUDIT.json` lists each component's actual operand references, native
metric keys, retained unused measurement references, populations and assumptions.
The exact source bytes and declared metadata bytes are retained beside them.

Selected values are read_count=2, GC/(A+C+G+T)=5/9,
Phred-implied expected errors=0.001 under the source-bound Phred33 assumption,
and Hostile native report retention=6/8=0.75. The native FastQC category is pass;
the population is complete; the supplied association remains unresolved. All
requested recipe-stage states remain unknown. `status=ok` means this explicit
requested projection was fulfilled, not scientific acceptance or task completion.

The synthetic bundle's task output path and UUID now agree with its synthetic
Workspace object. Its inherited `requested_selector_sha256` still names the
frozen195 example; this provider fixture does not reconstruct or authenticate a
full ResultSelector. The host integration owner must construct its actual exact
synthetic selector/bundle relationship and custody records before host delivery.
The earlier `integration_handoff_001` is preserved as exploratory evidence; it
also preceded this path/UUID correction and the final source freeze.

Reproduce the filled files by running `../export_handoff_002.py` after choosing a
new output directory; the script deliberately refuses to overwrite this export.
Its 24-source implementation pin and exact JSON hashes are in `SUMMARY.json`;
file hashes and export signatures are in `ARTIFACT_DIGESTS.json` and
`EXPORT_MANIFEST.json`. `../frozen_001/VERIFICATION_RECEIPT.json` records the
86-case frozen C test run and absence of concurrent source changes.
