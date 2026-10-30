# Additive declaration correction002

The initial001 builder and its four generated schemas remain unchanged.
Final normative declarations are REQUEST_SCHEMA_002, EXTRACTION_SCHEMA_002,
SHEET_SCHEMA_002 and RETURN_SCHEMA_002. The interface's scientific meanings and
proposed v2 version names are unchanged; no production or saved v2 data exists.

Three omissions in the first draft are corrected before implementation:

1. An authenticated unreadable fragment can retain a canonical image locator
   with quote=null. Geometry custody does not create invented literal text.
2. For a printed normalized ratio or percentage, signal_scale may be
   not_applicable; it is relevant to division of two raw printed signals. That
   state requires no manufactured common-scale witness. A visual_signal_pair
   must instead support its actual common scale or preserve an unknown/conflict.
3. A JATS representation has reading_state=not_applicable and an independent
   parse_status (parsed,partial,unavailable). Parser capability failure is not
   a conclusion that an image label is unreadable. Visual selections preserve
   their nominated reading state even if a dependency is unavailable; their
   parse_status/diagnostics then prevent numerical promotion.

build_declarations_002.py applies these precise declaration-only changes to
the original in-memory type graph and writes new exclusive filenames. It imports
no application and implements no scientific reader/calculator or model call.
The public interpretation TASK must distinguish these states. Root must review
the final declaration generation and examples before any fresh coding release.
