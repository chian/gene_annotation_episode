PARTNER_LEAD = "Investigate the assigned source evidence about a particular molecule's dependence on a particular partner. Select the relevant omission, addback and control observations, their experimental meanings and the applicable partner component readers and graders. Return the requested saved partner components with their actual subject, endpoint, conditions, uncertainty, provenance and unresolved inputs. Required partnership, genomic presence, coexpression, physical interaction and demonstrated function are distinct questions; this source investigation does not establish the other questions automatically.\n\nliterature.partner.source.populate reads selected literal source spans directly, without a prepared numerical dataset. literature.partner.populate uses a compatible retained selection dataset. Select the route whose actual inputs are available, preserve missing measurements and use the existing operation contract for complete operands."
A107_SOURCE_LEAD = 'Investigate the assigned source-reading question for A107, required partner presence and coexpression. Establish what the supplied source actually contains: partner-requirement experiments, genomic records, expression measurements or relevant context. These are different source questions. A supplied expression table can be inspected without finding an omission/addback experiment or establishing functional partnership first. Preserve declared feature and sample identities, conditions, quantity meanings, censoring, calibration, provenance and unresolved biological correspondence. Select the available reading, reasoning and narrower investigations according to the actual question. Return the requested typed findings and source-anchored records needed by the scientific parent for its next decision. This reading question does not by itself establish activity, necessity, target expression or annotation support.'

def selected_family(selected, sources):
    if selected and selected <= {'requested_partner_components'}:
        return 'partner'
    if not selected:
        if sources and sources <= {'literature_partner_cells'}:
            return 'partner'
        return 'A107_source'
    return None

def lead(family):
    return PARTNER_LEAD if family == 'partner' else A107_SOURCE_LEAD

def operation_family():
    return 'partner'
