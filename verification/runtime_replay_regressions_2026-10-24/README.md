# Replay regression diagnosis and test-only repair

Both original failures occur before tool execution or `controller_value`: they
attempt `fixture.measure` directly in the annotation root, where the current
contract allows no tools. Removing only the recent controller-input reuse block
in memory reproduces both failures exactly.

The approved repair changes only those two test functions to use existing
tool-owning children. It preserves the publication-interruption boundary,
idempotent recovery, original resource history and archive bytes, and explicit
separate parent/child observations. Root catalogs remain empty. All 231 non-cache
production files are unchanged.

- Original two tests: 2 failures both with and without controller-input reuse.
- Repaired pair: **2 passed in 21.22 s**.
- Same original selected regression suite: **30 passed in 119.33 s**.

The phrase "unchanged scripted tests" in `repaired-pair/RUN.json` is the generic
runner's statement that source was unchanged **during that run**. The two test
functions were deliberately repaired first. Their original text, the exact diff,
the original failed suite and both original failing comparison runs are retained.
No historical failure evidence was rewritten.

See [DIAGNOSIS.md](DIAGNOSIS.md) for the exact path and limits,
[test_runtime.diff](test_runtime.diff) for the test change,
[comparison.json](comparison.json) for the before-change proof,
[CHANGE_BOUNDARY.json](CHANGE_BOUNDARY.json) for source invariants, and
[selected-suite/RUN.json](selected-suite/RUN.json) for the final command and hashes.

Verification uses scripted synthetic runtime fixtures. It does not establish
live native execution, model decisions or scientific measurements. The separate
live NCBI BLAST verification was untouched.
