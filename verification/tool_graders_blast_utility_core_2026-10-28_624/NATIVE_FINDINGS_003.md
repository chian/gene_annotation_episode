# Native findings, original084 and diagnostic085

Original084: three explicit tiny makeblastdb preparations (nucleotide v4/v5,
protein v5), their info/metadata/extraction operations, plus/minus/past-end range,
duplicate selectors, mixed present/missing selector, full/stride integrity and a
duplicate-ID build:20 commands. Three preparations and all ordinary extractions
succeeded. Missing selector and duplicate-ID build returned1 with partial output.
Both integrity commands returned1; the one capture test therefore FAILED because
it had incorrectly expected integrity success. The immutable084 receipt is
terminal/quiescent with unchanged source/dependency/stdlib/binary pins.

085 retains the original databases, never rebuilds them. Four commands: v5 full
check with verbosity4 to diagnose the actual failure, first v4 full check, and a
nonpalindromic plus/minus sequence comparison. The diagnostic capture test passed
without requiring the two failed native integrity operations to pass. Native
checks report GetTaxInfo() - Taxid 9606 not found, and separately show OID0,1,2
PASS. This is partial sequence validation and a taxonomy lookup failure, not
proof of database corruption or a full integrity pass. Original database pins
are unchanged. No taxonomy record is fabricated and no new download selected.

Native extracted %l is full sequence length12 for a six-symbol range2-7 and a
five-symbol range8-99 clipped at the end. seqB2-7 is TGCAAT plus, ATTGCA minus.
Duplicate requested seqA appears twice as two original native output rows.

Writer metadata (.njs/.pjs) and blastdbcmd -metadata are DIFFERENT retained
observations. The writer lists6/9/9 components for v4DNA/v5DNA/v5protein and omits
its own metadata file. Captured complete inventories contain7/10/10 files.
blastdbcmd -metadata includes that metadata file and reports a corresponding
larger native bytes-total. Preserve each observation's exact source and file
population. Native reported byte totals are never substituted for actual capture
byte totals or silently compared across these two populations.

No installed grader count or finished tool count changes from these observations.
Episode wiring and actual bound result paths remain unfinished.
