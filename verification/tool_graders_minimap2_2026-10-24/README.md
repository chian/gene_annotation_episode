# Minimap2 numerical-module verification, 2026-10-24

This directory retains real executions of the pinned minimap2 2.31-r1302
binary on explicitly synthetic small DNA sequences. It does not assert a
biological annotation or complete episode-path integration.

`run_native_fixtures.py` executed six distinct selected presets: map-ont, map-pb,
map-hifi, lr:hq, map-iclr and sr. Every native invocation used the existing
`run_local_job` lifecycle at 20 GiB RAM and 4 GiB scratch, without a wall-time
budget. Each `receipt.json` records the exact command, zero native return code,
cgroup enforcement and observed scratch allocation. The selected `--frag=no`
invocation maps unpaired FASTA inputs; no FASTQ qualities were used.

Each preset retains full input FASTA, native PAF, stderr, runner receipts, full
populated sheets and calculated placement scores in `placements.jsonl`, and
per-query components in `query_scores.json`. There are three placements per
preset, 18 actual native rows total. All six presets produced the following
same geometric results on these particular inputs; their native score tags and
selected modes remain separately preserved.

| Measurement | Forward and reverse fixtures | Exact fixture |
| --- | ---: | ---: |
| Query span | 2398 | 2000 |
| Reference span | 2400 | 2000 |
| Paired positions | 2397 | 2000 |
| Inserted / deleted bases | 1 / 3 | 0 / 0 |
| Full alignment columns | 2401 | 2000 |
| Native matches / block | 2392 / 2399 | 1999 / 1999 |
| Native ambiguity `nn` | 2 | 1 |
| Normalized `cs` equal / substituted | 2393 / 4 | 2000 / 0 |
| Supplied original-symbol equal / substituted | 2392 / 5 | 2000 / 0 |

The forward/reverse CIGAR is `1700M1I399M3D298M`. Native identity is
2392/2399 = 0.9970821175489787; query paired coverage is
2397/2398 = 0.9995829858215179. An original reference R versus query Y becomes
normalized N versus N, explaining why `cs` equality exceeds original equality.
An ambiguous insertion contributes to `nn` and full geometry, and is excluded
from native `blen`. The exact fixture demonstrates that original-symbol
equality may include matching ambiguous symbols while native matching excludes
that column.

The synthetic hand-check contract separately gives qlen=7, query=[1,6),
rlen=10, reference=[2,8), `cg=2M1I2D2M`, `cs==C*gt+g-tc=GT`:
paired=4, insertion=1, deletion=2, columns=7, native identity=3/7,
query paired coverage=4/7, reference paired coverage=4/10, query span
coverage=5/7 and reference span coverage=6/10. Unit tests assert those exact
values, plus boundaries, skips, reverse coordinates, missing information,
malformed/contradictory native rows, invalid joins, repeated/alternative
correspondence, exact duplicates and partial/unknown output.

Pinned source inspected: `minimap2.1` OUTPUT FORMAT; `align.c`
`mm_update_extra` and `mm_update_cigar_eqx`; `format.c` `write_cs_ds_core`,
`write_cs_ds_or_MD`, `write_tags` and `mm_write_paf4`. These establish native
field meanings, ambiguity exclusion, reference skips, normalized symbols and
native P/S/I/i categories. No SAM supplementary flag is inferred from PAF.

`recalculate_saved.py` uses saved sheets alone and explicitly forbids socket
creation/connections and subprocess execution. It checks that all 18 placement
score results reproduce exactly, recalculates the 18 per-query summaries and
checks that input sheets remain unchanged. `recalculation_report.json` records
the result. It does not rerun minimap2 or reacquire an input.

The module-focused pytest command and its actual final result are retained in
`test_results.txt`. This worker did not edit the runtime, Store, schemas,
publication/admission consumers or tool information library. The root task
separately owns production binding, exact artifact custody, episode-owned
invocation, typed returns, action/credit counts and broader site extraction.
Those properties are not established by these standalone module tests or
native fixture commands. No pending NCBI verification was inspected or changed.
