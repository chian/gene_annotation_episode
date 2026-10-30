# Final closed-parent-grammar declaration correction005

Final normative files are INTERFACE_005 and REQUEST_SCHEMA_005,
EXTRACTION_SCHEMA_005, SHEET_SCHEMA_005 and RETURN_SCHEMA_005.
001 through004 remain unchanged design history.

The existing parent communication grammar requires every scalar to declare its
type explicitly. A JSON Schema string const alone is valid Draft202012 syntax
but does not satisfy that stronger grammar.005 adds type:string to const nodes
in the returned-fact projection, including nested domain meaning. It does not
change any allowed value, field, scientific meaning or runtime behavior. The
request/extraction/sheet schema contents equal004 exactly.

The declaration check will compile a whole closed parent form using the actual
existing validate_closed_schema function. That checks grammar only, not future
registration of this proposed fact source or actual C1/C4 execution. No new
communication exception or special schema bypass is needed or authorized.
