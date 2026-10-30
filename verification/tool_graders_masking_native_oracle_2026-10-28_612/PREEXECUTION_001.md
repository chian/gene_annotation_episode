# Selected native oracle cases and custody — 612

ORACLE_CASES_001.json was written before execution. It fixes all synthetic input
bytes, input record ordinals/headers, binary identities and selected argv tokens.
The only substitutions bind declared executable, input and oracle directory paths.
The selected count-generation command precedes separately selected masking commands
that consume exactly its output; a failed count command does not cause a retry,
substitute reference or fallback counts.

All commands, including help/version, run in check064 via the existing529 runner.
The native_executable list supplies snapshot paths; host binary paths are never
executed. Existing check005/dependencies is the dependency closure.

The retained immutable ORACLE_MANIFEST.json will contain version, attempt, plan pin,
software pins, input pins with original record ordinal/header/sequence, cases,
artifact pins, and limitations. Each case records exact argv (also CLI JSON bytes),
returncode or unavailable, status, selected parameters, omitted-native-default
qualification, exact input identifier, statistics-source case and consumed pin,
stdout/stderr and primary-output relative path/sha256/size or explicit absence.
Failed or empty output is not an unmasked result. All retained byte artifacts are
sealed read-only after capture; the manifest also receives a separate SHA256 seal.

Tests independently compare native interval positions with soft FASTA lowercase
positions on the same records and retain ordinal-based concordance. Inclusive
START-END corresponds to half-open [START, END+1). DUST hard FASTA is compared
against its interval oracle to expose masked pre-existing Ns invisible to
case-insensitive symbol differences. Acclist is an inspected native format only.
Statistics parsing here is a tiny format assertion, not a second production parser
or calculator. Parent owns shared numerical implementation and episode bindings.
