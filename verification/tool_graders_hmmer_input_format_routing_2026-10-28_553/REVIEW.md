# Native format routing repair

This records implementation evidence under the existing user-entered goal.
No goal or scope requirement changes.

The collected check013 integration attempt had 242 passes and 25 failures.
Source/runtime/native and retained-fixture hashes were unchanged; import and
native mapping audits were clean. Its exact case reports remain in packet529.

The actual native compiler retains FORMAT_ARGUMENTS values such as AFA, A2M,
Stockholm, Pfam, Clustal and PHYLIP in operation.settings. The new data dispatch
was comparing these against canonical lowercase reader formats. This repair
normalizes only the local dispatch variable. It does not modify saved settings,
requested argv, formats, historical sheets, calculators or operation schemas.
Repair551 owns the matching comparison-only validator normalization.

Sixteen adapter-test failures passed incomplete settings to local context
validation: an AFA or SELEX source requires its original declared format in the
settings. Those tests now supply that format while retaining alphabet and
numerical assertions. Local validation is not relaxed. The full-episode test
now expects the original compiler-declared native argument spelling in settings;
its retained source format remains canonical. Eight new pure regression cases
check six actual native input spellings and two output spellings through the
same sheet, calculator and source alphabet handoff.

The numerical writer Unicode defect and retained-native regrading are owned by
552; population qualification/no-record validation defects are owned by551.
No application import or test ran while authoring this repair. AST parsing
succeeded. All runtime outcomes remain for bounded verification.
