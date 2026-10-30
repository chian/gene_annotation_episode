# SAMstat native-output boundary workload

This workload supplies the missing native-format and numerical-field contract
for the existing BV-BRC FastqUtils grader. It may collect source, execute tiny
native producers in its own directory and define interfaces. It may not edit
production, the 198/204 candidates, user design records, inventory scope or
another worker's evidence. Coding assignments follow the concrete contract.

The inspected real caller is retained in
`verification/tool_graders_bvbrc_fastqutils_contract_2026-10-25_193/sources/p3_fqutils/lib/fastq_utils.py`,
complete `run_alignment` function. It invokes `samstat` on `.all.bam`, then
deletes that input during cleanup. The retained `.aligned.bam` is filtered with
`samtools view -F 4`; it cannot replace the original input denominator. A
failed samstat process produces an HTML error stub, not a successful numerical
report. An HTML filename is not proof of format or successful execution.

The primary upstream source is https://github.com/TimoLassmann/samstat.
Record exact commit/version, source bytes and executable version; repository
presence cannot establish which version is deployed on BV-BRC. Prefer source
and native execution over guessing data from rendered graph pictures.

Required evidence: full numerical payloads in actual HTML, their population
and mate/reference relationships, observed versus normalized/smoothed values,
native mapping-quality bins, sequence versus alignment-record denominators,
read-position coordinates, missing qualities, paired/secondary/supplementary
alignments, unmapped records, empty/partial input and error-stub behavior. Use
small SAM/BAM/FASTQ inputs with known counts; preserve native reports, commands,
versions, stdout/stderr, timings, hashes and precise numerical examples. Do
not execute scripts embedded in an acquired HTML file. Any parser must parse
the supported data grammar deterministically without JavaScript execution.

Output files owned by this workload: `SOURCE_RECEIPTS_001.json`, retained
`sources/` and `native_examples_001/`, `NATIVE_FIELDS_001.json`,
`PARSER_CALCULATOR_PORTS_001.md`, `WORKLOADS_002.md`, and a final evidence report.
Record later corrections additively. Numerical-field rows must define exact
native fields, units, population/denominator, coordinates, precision,
uncertainty, missing behavior and data identity. Do not encode a score DSL or
turn mapped/unmapped categories into annotation-confidence numbers.

Map the actual format to the current FastqUtils NativeDocument, Cell,
Population, NativeSection, NativeLabel and RawBlock ports from 204, or identify
an explicit necessary extension. Define exact parser and calculator functions,
metadata joins, typed success/partial/failure shapes, consuming functions and
independent owned files before suggesting coding work. Reuse existing
composition/quality/retention/mapping arithmetic only if the numerical meaning
and populations match. Native report values need not be recomputed into new
scores merely to have a calculator.

The consuming path remains child-owned API execution -> selected Workspace
bytes -> existing FastqUtils provider -> sheet/calculators -> original requested
typed return. No new episode, LLM grader, acquisition inside a parser,
autonomous workflow, root tool or evidence-axis redesign is allowed.

Read the complete original goal before work and reread its objective and all
16 design principles after substantial source/native examination, before
translating facts into fields and interfaces. Source facts cannot override
that design. Local work stays within20GiB RAM and4GiB scratch, with no wall-time
cap. Do not install globally, use Aurora, guess credentials, or claim live
BV-BRC deployment. An unavailable build dependency stays an explicit fact;
continue source and retained-native contract work where possible.
