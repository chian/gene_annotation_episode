"""Present original existing evidence-axis guidance without loading a process library."""

from copy import deepcopy
import re


def evidence_axis_instruction_view(entry):
    """Present existing measurement guidance, never the draft scoring sheet.

    The retained v1 record has no separately reviewed investigation prompt.
    This limited view preserves its scientific measurement guidance as text;
    it does not promote criteria, grading levels or reader metadata to TASK
    instructions. Internal resolve() continues to return the exact raw record.
    """
    title = entry['name']
    description = entry.get('description', '')
    if description.startswith('Score '):
        description = 'Investigate ' + description[len('Score '):]
    paragraphs = [
        f'Investigate the supplied target using {title.lower()}. Start from the supplied '
        'sequence, selected file contents or snippets, retaining their boundaries, completeness '
        'and known context. An initial candidate annotation or publicly searchable name is not '
        'required. Possible functions can emerge from the evidence and can then be compared '
        'or revised.',
        description,
        'Obtain actual measurements from the relevant literature or dataset analysis. Retain '
        'the measured subject, source, conditions, controls, units, bounds and uncertainty. '
        'Keep the finding on its original subject separate from the relationship that makes '
        'it informative about the supplied target. That relationship is not restricted to '
        'sequence homology. Missing information remains unknown; repeated representations '
        'of one experiment remain one experiment.',
    ]
    seen = set()
    for metric in entry.get('native_measurements', []):
        guidance = [f"Examine {metric['name']}."]
        for line in (*metric['method_requirements'], *metric['comparison_limits']):
            # These fields mix useful scientific limits with historical reader
            # implementation and scoring-policy notes. Neither belongs in the
            # investigation. Keep the original useful guidance verbatim.
            if (line in seen or re.search(
                    r'\b(?:extractor|JSON pointer|Store metric)\b'
                    r'|this workflow|unavailable extraction|negative.log10|summing their scores',
                    line, re.IGNORECASE)):
                continue
            seen.add(line)
            guidance.append(line)
        paragraphs.append(' '.join(guidance))
    return {key: deepcopy(entry[key]) for key in ('id', 'name') if key in entry} | {
        'instruction_status': 'limited_existing_measurement_guidance',
        'investigation_instructions': '\n\n'.join(text for text in paragraphs if text),
    }
