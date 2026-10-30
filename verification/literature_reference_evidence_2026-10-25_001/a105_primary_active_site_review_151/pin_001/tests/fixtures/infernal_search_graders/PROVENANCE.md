# Infernal search native fixtures

These are actual Infernal 1.1.5 outputs, executed on 2026-10-26 UTC with the
existing local durable job runner. Complete stdout contains native alignments;
the table parser does not reconstruct residue correspondence from spans.

The commands, binary/input/output hashes, return codes, resource enforcement
and original working directories are retained in each `*.receipt.json`.
All native processes exited 0. `--cpu 1` was explicit for searches. The resource
policy was 20 GiB RAM, 4 GiB scratch and no wall limit. Receipts confirm cgroup
MemoryMax=21474836480, MemorySwapMax=0 and RuntimeMaxSec=infinity. Scratch was
monitored with possible overshoot, with a hard per-file limit; maximum observed
scratch across the ten native operations was 303104 bytes. Peak RAM was not
measured in these receipts.

Original tutorial sources were copied before use:

* tRNA5.c.cm: b5ed07f9f442d7e639b3324f79ae6209b956a57426174bec1d7f441af6785450
* tRNA5-hand.c.cm: d9497a8c655a8bb764053831ae5b5ac19248377097f8808ef22431dc18b0f804
* mrum-tRNAs10.fa: 458183dae273c27cc934236c4ffd1f70f24681028751ad198e7b8a4430ce7c91

`two_models.cm` is the byte concatenation of the two native tutorial CMs.
`tiny.fa` contains tutorial tRNA 1 (native_forward), its explicit reverse
complement (native_reverse), two copies separated by 50 A residues
(native_repeat), and tutorial tRNA 2 (native_second). `no_hits.fa` is a deliberately
constructed 160-A negative-test input. These modified input sequences are test
operands, not new experimentally observed biology. The output measurements are
real native calculations on those operands. No output rows were synthesized in
the native fixtures; deliberately mutated cases are constructed explicitly in
the test functions.

Native cases cover cmsearch formats 1/3, cmscan formats 1/2/3, both programs'
zero-hit outputs, cmsearch mixed !/? inclusion, and cmsearch HMM-only scoring.
Format-2 omitted-index -1, legacy tables without length columns, malformed cells,
contradictory declarations and wrong associations are explicitly synthetic
tests derived from the retained rows; no live -1/legacy-output claim is made.

The fixture MANIFEST.json hashes every copied native input, output and receipt.
The originating run files and cmpress outputs remain under
verification/tool_graders_infernal_search_2026-10-26_219/native/.
