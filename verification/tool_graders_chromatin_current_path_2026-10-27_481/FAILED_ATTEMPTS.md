# Verification-wrapper preparation failures

Neither failure below reached pytest or scientific execution. They are owned
verification-wrapper errors, not failures of the production chromatin path.
No production or existing test/helper file was changed to repair them.

1. `cooler001` staging initially reached `local_jobs → acquisition → domain`
   under the administrative Python `-S` launcher without placing the copied
   dependency site on `sys.path`. Importing jsonschema failed. There was no
   handle and no dispatched work. `pre_dispatch_failure.json` records this.
   The owned launcher now includes the already-frozen dependency site and has
   an explicit `dispatch` operation that rejects any existing handle. This
   allowed dispatch of the same fully staged snapshot without recreating it.

2. The resulting `cooler001` handle was
   `gene-local-job-d68505642d0c426d98d1bea64e13b1d2.service`. Its bounded
   provenance wrapper attempted `ldd` on every shared object, including
   `scipy.libs/libgfortran-83c28eba.so.5.0.0` as a standalone entry point.
   That loses the caller extension's wheel RPATH and reported a missing sibling
   library. The wrapper raised `selected_binary_dependency_missing` before
   importing pytest. Its terminal/quiescent exit1 was collected, with all source,
   dependency, interpreter and standard-library pins unchanged.

The corrected wrapper resolves Python extension entry points and their
transitive library dependencies, preserving their RPATH. All actually loaded
executable mappings are still checked against the resulting pins after tests.
The explicitly selected `cooler002` and `hic001` runs reused the exact immutable
dependency files via hardlinks into distinct attempt trees, froze current
source again, and both reached collection of all seven existing tests.

The original `cooler001` handle and frozen files remain intact. No observation
timeout or live-handle delay triggered a restart. Historical SIGSEGV-11 causes
from older packets remain unproven and are not explained by these wrapper fixes.
