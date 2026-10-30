# Native evidence and proposal corrections

This adds check102/check102c facts to the unfrozen642 proposal. It does not alter
native receipts or declare any utility integrated. All paths below are under
`verification/tool_graders_blast_preparation_native_2026-10-28_644/` unless stated.

The planning owner read `OBSERVATIONS_001.json` in full and the original
`runner_evidence/receipt.json`. The receipt records rc0, terminal/quiescent,
unchanged source/dependencies/stdlib/binaries,20GiB RAM,4GiB scratch,0swap and no
wall limit. This is the capture test result, not success of all native calls.
The16 native calls include11 successes and5 failures. Their exact argv/outcomes,
closed writers and inventory flags were inspected in
`retained_native/CAPTURE_001.json`, with the actual ordered original input text
from `retained_native/OPERAND_BINDINGS_001.json` and preserved-input assertions
from `retained_native/ASSERTIONS_001.json`. No database bytes were opened by642.

Observed GI stderr is exactly `Converted 3 GIs into binary GI file`, with no
captured malformed-line warning. Its input retains duplicate9 and malformed
not-a-gi. Native converted count3 and binary20 bytes do not by themselves prove
unique stored count. This corrects the initial expectation of a captured warning.

The two aggregation aliases retain DBLIST order A,B versus B,A, native NSEQ6 and
LENGTH66. Both inputs are physical copies of the same original tiny096 database;
these are not independent biological sources. Original DB closure has10 pinned
files. The new index adds two files beside its writable copy; original/staged
input files remain unchanged. The old-style legacy index has its native map.
Actual index warnings, absence of nonempty filter rows and all profile failures
are preserved in642/001. No native helper was automatically invoked.

The planning owner read the entire retained
`official_source/seqidlist_writer.cpp` plus complete relevant
`SeqDB_ReadMemorySiList` and `SeqDB_ReadSiList` functions in
`official_source/seqdbcommon.cpp`. Source writer uses CSeq_id parsing and
GetSeqIdString(true) with PIR/PRF exception, sorts/uniques, and optionally filters
against a v5 DB via AccessionsToOids. The alias reader first tries the v5 binary
list, otherwise keeps literal text tokens after whitespace/comment handling.
This explains a semantic distinction; it does not authorize identifier rewriting
in staging. Source acquisition's separate receipt reportedly has rc4 from a
DNS-library audit discrepancy even though5 sources were downloaded;642 does not
promote that acquisition receipt to a clean pass.

Root separately selected check102c with the unchanged captured bound.bsl and
the exact original096 DB. The planning owner inspected:

* `retained_binary_alias/CAPTURE_002.json`: both exact argv, outcomes, stdout and
  retained native_alias_text;
* `retained_binary_alias/RETAINED_BINARY_LIST_DECODE_002.json`: full decoded native
  schema evidence, source identity and native byte order;
* `retained_binary_alias/ASSERTIONS_002.json` and
  `binary_alias_runner_evidence/receipt.json`: unchanged inputs, two selected
  calls, both rc0, clean pinned bounded runner receipt.

The retained98-byte bound.bsl has SHA256
`83ba9e9aa335a18121b1cdf0727652e4ab8399f5c92deec9b0bc00716addc68e`
and stores `KEEP_B`. Binary-list subset alias succeeds with:

```
DBLIST "db/tiny"
SEQIDLIST bound.bsl
NSEQ 1
LENGTH 13
```

The separately selected extraction reports native OID1, identifier lcl|KEEP_B,
length12 and sequence TTGCAATTGCAA. Therefore642's initial text-only subset
restriction proposal is corrected to `format: text|seqid_list_binary`.
The historical text-list failure remains unchanged. Alias LENGTH13 is retained
as native reported alias metadata; it is not exact extracted length12 and is
not corrected by subtracting one. This single example does not establish a
general correction formula or search compatibility.

Profile evidence remains: the authentic26-row232-residue input failed RPS with
PSSM-too-large; eleven sequence DB files survived and profile files did not.
Successful info on those surviving files reports1 sequence/232 residues and is
not successful RPS preparation. DELTA/COBALT failures remain preserved. A later
candidate28-row authentic profile input had been reported by644 at the initial
addendum drafting. Its subsequent sealed result is added below; earlier failed
input facts are not changed.

Existing implementation evidence was also inspected directly in529:
`check096_blast_utility_full_workflow` has3 passing tests/clean rc0;
`check098_blast_utility_capture_semantics` has rc4/no tests;
`check098b_blast_utility_capture_semantics` has472 passed plus one stale assertion
expecting partial instead of complete captured bytes;
`check098c_blast_utility_practical_assertion` has the corrected targeted pass.
These historical failures remain facts and do not redefine638 capture semantics.

The unfrozen proposal was aligned with643 and root: all new operation branches
use operation_v2 within the same shared authority; old v1 records stay exact.
`CLOSED_PORT_TYPES_002.md` supplies helper row schemas and uses existing generic
identity values, avoiding unnecessary prepared-identity changes.

## Added sealed check102d evidence

The planning owner subsequently read the sealed
`retained_profile28/CAPTURE_003.json`, `INPUT_BINDINGS_003.json`, and
`profile28_runner_evidence/{receipt,execution_audit}.json`. Exactly one selected
makeprofiledb RPS command returned0 with empty stdout/stderr, closed writers,
complete captured bytes and twelve generated database-family files. The runner
receipt and execution audit are clean with all original/source/binary pins
unchanged and the same bounded policy.

The input is an authentic query-bearing28×320 PssmWithParameters object from315's
retained webpsi.2ndround.ss.asn: original SHA256
`0862ae299a0223945ef7328500ef1e0aa242ccc328f401c408b27c396f08be48`,
exact object byte interval[101,421058), object SHA256
`a5997b2ac62c529701b148895cf9d409c204db431f564925c7df172998aff1a8`.
Only the standalone type prefix and final newline were added; wrapped SHA256
`a7ce96b9dae4e3a818c2dfb6e031606541791ba02840181fa1a9a83f9e30b85b`.
The selected profile/list are complete authentic inputs. No source field, score,
frequency, query, alphabet row or biological measurement was changed. The frozen
input-boundary qualification predates the native run and remains unchanged.
This verification wrapper does not authorize production to discover or repair
nested inputs automatically; a parent supplies the concrete selected profile.

Native profile files: .aux70 bytes, .freq35968, .loo544812, .rps35968, plus the
captured eight protein-sequence DB files. Auxiliary text is:

```
BLOSUM62
11
1
0.000000e+00
0.000000e+00
0
0
1.000000
320
3.756720e-02
```

This establishes an actual successful single-input RPS family and the native
aux parser example: matrix BLOSUM62, gap-open11, gap-extend1, scale1, one native
length/K pair320/0.0375672. Header lines4–7 remain writer placeholders. No native
included-profile count diagnostic or consuming-search validation was produced.
The prior26-row RPS failure and surviving readable sequence-DB counterexample
remain unchanged. Successful DELTA/COBALT, binary scoremat, exclusion and
multi-volume membership/effective-parameter coverage remain explicit native
verification dependencies. No preparation operation is integrated by this test.
