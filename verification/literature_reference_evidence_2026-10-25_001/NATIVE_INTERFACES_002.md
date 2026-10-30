# Additive interface correction after original-source execution

NATIVE_INTERFACES_001 remains the pre-coding contract. The actual original XML
includes the normal external JATS PUBLIC DOCTYPE. The reader now accepts a finite
external article PUBLIC/SYSTEM declaration without fetching/loading it or
changing source bytes. Internal subsets/custom entities remain unsupported.
This adjusts source parsing, not experimental interpretation.

Native numeric returns use reported_subject_ref, not assayed_subject_ref. Literal
subject-token presence does not establish an assayed molecule. experiment_ref
and condition_ref are null until actual experimental relationships are extracted;
a paragraph locator is not an experiment identity. Both quantity_ref and
analyte_ref accompany reported numbers; Km and activity cannot be interchanged.

Km's correction cells are unavailable with quantity_not_activity_rate; they do
not misleadingly request activity-correction measurements for a kinetic parameter.
Specific-activity source cells cannot silently populate the different unnormalized
q/g/E boundary. That source's unmeasured correction inputs remain null.

Native source cells use the separate literature_quantity_cells fact source and
requested_quantity_components assignment field. Existing literature_rate_cells
and original comparison semantics remain intact. The native source operation
accepts only source custody/selectors, literal expected subject, quantity role
and analyte. It accepts no model-supplied measurement number or ± definition.
The report's reported_uncertainty_kind accompanies every admitted cell.

The current selected operation does not yet bind complete scientific assay context
or supported source primitives into the full correction calculator. That remains
unfinished, rather than being replaced with a default reliability number.
