The actual installed-package test reproduced a return-array ordering defect.
Canonical JSON storage alphabetizes object keys; the FastqUtils return function
iterated saved adapter_result.facts keys to construct component arrays. The
original requested component order was gc, errors, retained. After storage it
became errors, gc, retained. Every numerical row was otherwise identical.

The candidate return function now iterates the validated original RequestedForm
field order. It preserves the existing empty-invalid-result behavior and all
native-value, source, original-selector, content-binding and custody checks.
One regression case checks both an actual canonical JSON round trip and reversed
saved-object insertion order. It does not sort or rewrite original native rows.

Only the return module and its test changed. The 24-file scientific provider pin
is unchanged. Prior package attempts, the frozen 1095-file source and earlier
development histories retain their original bytes and results. The corrected
candidate requires its own return/package and final episode-path verification.
