REACTION_LEAD = 'Investigate the assigned source evidence about reaction predictions, measured ratios or resource constraints. Select the relevant measurements and source meanings, then use the applicable reaction component readers and graders. Return the requested saved components with their actual molecule, chemical species, endpoint, units, conditions, provenance, dependence and unresolved inputs. Chemical bookkeeping, measured molecular activity and physiological feasibility are separate conclusions.\n\nliterature.reaction.source.populate accepts exact reported-number and source-unit selectors directly; the host retains the selection recipe and uses the original native reader and component calculator. Choose this route for usable paper evidence without a prepared numerical dataset. Predictions and resource-model parameters remain explicitly interpreted rather than measured values.\n\nFor literature.reaction.populate, source_ref identifies the evidence source. data_source_ref identifies a compatible retained measurement dataset or native source-selection recipe. Supported retained dataset versions are a110_source_reaction_measurements and a110_source_reaction_meaning_measurements; a110_source_reaction_selection holds native source selectors. A supplied compatible dataset can be used directly, without re-extracting its numbers into selectors. Declared synthetic operands can yield conditional components while retaining synthetic origin, unknown biological applicability and unresolved target correspondence. Their calculation does not require first establishing chemical identity or protein activity. A declared chemical equation or formula panel is not automatically a measurement dataset. The existing operation permits data_source_ref=null when no supported dataset or source-selection route is available, preserving unavailable components and their missing reasons. Do not invent measurements to fill them. Use the actual source and operation contracts to decide what is supported.'
REACTION_VIEW_MEANING = 'The numerical and semantic return views have different input requirements. A numerical measurement dataset supplies literature_reaction_cells but has no retained source-bound model/resource meanings for literature_reaction_semantic_cells. Repeating that population or adding literal identity bindings does not create the semantic view. For requested semantic cells, select an actually received meaning dataset or use literature.reaction.source.populate with the supported native source selectors and their source-bound meanings. Unsupported identities remain unknown; a conditional model definition is separate from a measured value. If the available evidence cannot support a meaning, preserve that missing reason. These are views of related evidence, not independent confirmations.'
A110_SOURCE_LEAD = 'Investigate the assigned source-reading question for A110, biochemical feasibility and chemical/resource accounting. Establish whether the supplied source contains declared chemical equations, measured ratios, model predictions, resource observations or relevant context. Keep those meanings separate and preserve the actual species, quantities, units, conditions, model assumptions, provenance and missing inputs. Inspecting a declared equation panel does not require an activity experiment or make it a measurement dataset. Choose available reading, reasoning and narrower investigations according to the actual question, and return the requested typed findings and anchored source records needed by the scientific parent. Balance, a supplied reagent quantity and a source claim do not by themselves establish physiological feasibility or target activity.'

def lead(family):
    return REACTION_LEAD + '\n\n' + REACTION_VIEW_MEANING if family == 'reaction' else A110_SOURCE_LEAD



def selected_family(selected, sources):
    """Which A110 literature lead a leaf follows (owner, R10 of ``LOST_CONTENT_a110.md``): a literature leaf grades
    into the reaction sheet only when the reaction cells are requested; otherwise it does A110 source reading.
    ``selected`` are the requested reaction fields of the assignment, ``sources`` the fact sources the parent
    asked for."""
    if selected and selected <= {'requested_reaction_components', 'requested_reaction_native_positions'}:
        return 'reaction'
    if not selected:
        if sources and sources <= {'literature_reaction_cells', 'literature_reaction_semantic_cells',
                                   'literature_reaction_native_observations'}:
            return 'reaction'
        return 'A110_source'
    return None


def operation_family():
    return 'reaction'
