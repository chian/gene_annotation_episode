# Verification failures and corrections

These are additive verification records. The original immutable goal and
accepted contracts control the implementation; test expectations do not.

1. Initial projection test collection used pytest's reserved parametrization
   name `request`. Collection failed. The parameter was renamed `request_id`.
2. Four hand-entered native expectations were incorrect. Inspection of the
   retained upstream bytes established first v4 segment length 13 (not 236),
   first backbone member span 32 (not 10), first BBCols width 19 (not 10), and
   XMFA block 0/column 0 literal T count 1 (not 2). The expectations were fixed;
   production calculations were unchanged. The next projection run passed all
   27 then-existing checks in 10.23 seconds.
3. Unsupported actual XMFA version `Mauve2` initially resolved a slot because
   the parser retained a nonnull partial document. A malformed native `?`
   coordinate initially caused outward schema validation to reject the whole
   invocation. The independent original fixtures and results are retained in
   `edge_cases/`. Root reviewed the native parser, coordinate and D relationships
   and issued accepted `BUNDLE_NATIVE_EDGE_CASES_012.md`. E now retains the
   parsed documents, marks unsupported-version slots incompatible, and emits a
   precise `projection_target_incompatible` cause for an unrepresentable
   coordinate while preserving the full D row and independent facts.
4. Three added transfer tests initially constructed malformed outer transfer
   contracts: observed range width did not match body byte count, object=yes
   contradicted total size, and requested_range used an object instead of the
   actual two-element array. The actual ArtifactBundle validator correctly
   raised `range_byte_count_conflict`, `object_size_conflict`, and
   `contract_shape_invalid`. The fixtures were corrected to real partial
   transfer shapes and `[start,end]`; production code was not relaxed. The next
   full then-current E run passed 154 checks in 21.06 seconds.
5. Source review and a focused barrier uncovered scientific recomputation
   inside D's existing native component validators. The strict saved replay
   regression is deliberately retained as failing, not hidden behind xfail or
   an E workaround. See `SAVED_VALIDATION_ARITHMETIC_AUDIT_003.md`, the exact
   stack and dynamic trace. Root owns the correction and final pin refresh.

The small fixture-generation script initially attempted to index a direct
coordinate result through a nonexistent `value` key, and initially used the
wrong literal sequence prefix for the `?` mutation. Those verification script
errors were corrected using the actual source bytes; no production path or
native output was changed to accommodate them.
