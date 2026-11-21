"""MetaCATS as plain library functions: the groups code builds from a held alignment, the files the job takes, the reader
of the service's result table and the grading of it into the sheet the head's credit reads.

What was established against the live service (design note ``docs/plan/designs/bvbrc_metacats_episode.md``; probes
``runs/metacats_probe_3c`` and ``runs/metacats_probe_4b``):

* the deployed application takes ``input_type`` ``files``, ``alphabet`` ``aa``, ``alignment_file`` and ``group_file`` (workspace
  paths), ``alignment_type``, ``p_value``, ``output_path`` and ``output_file``;
* the group file is TSV with one header line (``Seq_ID<TAB>group``), then one line per sequence: the identifier (the first
  word of the alignment's FASTA header) and the group label. The groups are the values of the second column;
* A SEQUENCE OF THE ALIGNMENT THAT IS IN NO GROUP IS NOT LEFT OUT: the service makes it a group of its own (``Unlabeled``,
  the first group column of the result table, and the table's statistics change). So an alignment given to the service
  holds exactly the sequences of the groups: ``derived_alignment`` is the held alignment without the target's row (and
  without any sequence of no group), with the same columns;
* the result files are ``<header of the group column>-chisqTable.tsv`` (only the positions whose chi-square p-value is below
  ``p_value``; columns ``Position``, ``Chi-square_value``, ``P-value``, ``Degrees_of_freedom``, ``Fewer_5`` and one column
  per group, in the order of the sorted labels, holding the residue counts ``13 C, 9 S``; a gap is counted as the residue
  ``-``; a group with no residue there holds nothing) and ``<header>-mcTable.tsv`` (the pairs of groups that differ at the
  position, with the multiple-comparison p-value). ``Position`` is the 1-based column of the alignment.

Group labels are written by code (``group_01``, ``group_02``, in the order of the sorted product names): the service cuts a
label at its last ``/``, and a product name has one (``CspB/CspG/CspI``). The sheet keeps the product of each label.

Nothing here contacts a service or a store."""
import re
from statistics import fmean

GROUP_HEADER = 'group'
CHISQ_FILE = GROUP_HEADER + '-chisqTable.tsv'
MC_FILE = GROUP_HEADER + '-mcTable.tsv'
ALIGNMENT_FILE = 'alignment.afa'
GROUP_FILE = 'groups.tsv'
P_VALUES = (0.05, 0.01)
MINIMUM_GROUP_SIZE = 2
MINIMUM_GROUPS = 2
SCHEMA = 'metacats_sheet_v1'
_COUNT = re.compile(r'(\d+) (\S+)')


def parse_alignment(text):
    """The rows of an aligned FASTA as ``[(identifier, aligned sequence)]``: the identifier is the first word of the header."""
    rows = []
    for line in text.splitlines():
        if line.startswith('>'):
            rows.append([line[1:].split()[0], ''])
        elif line.strip():
            rows[-1][1] += line.strip()
    if len({name for name, _ in rows}) != len(rows) or len({len(sequence) for _, sequence in rows}) > 1:
        raise ValueError('alignment_rows_must_have_distinct_names_and_one_length')
    return [(name, sequence) for name, sequence in rows]


def build_groups(members, target_id, sequences):
    """The groups of the alignment, one per product candidate, built by code: ``members`` is ``{sequence identifier:
    product}`` (the reference sequences of the candidates), ``sequences`` the identifiers the alignment holds. The target
    is in no group; a member the alignment does not hold is not in a group; a candidate with fewer than
    ``MINIMUM_GROUP_SIZE`` sequences makes no group. Each group is ``{'label', 'product', 'ids'}``, in the order of the
    sorted product names; the ids keep the alignment's order."""
    held = [name for name in sequences if name != target_id and name in members]
    products = sorted({members[name] for name in held})
    groups = [{'product': product, 'ids': [name for name in held if members[name] == product]} for product in products]
    groups = [group for group in groups if len(group['ids']) >= MINIMUM_GROUP_SIZE]
    return [{'label': 'group_%02d' % (number + 1), **group} for number, group in enumerate(groups)]


def group_file_text(groups):
    """The group file of the job: a header line, then one line per sequence of a group."""
    return 'Seq_ID\t' + GROUP_HEADER + '\n' + ''.join(name + '\t' + group['label'] + '\n'
                                                     for group in groups for name in group['ids'])


def derived_alignment(rows, groups):
    """The aligned FASTA the job takes: the rows of the sequences of the groups (the target's row, and any sequence of no
    group, are left out), with every column of the held alignment kept."""
    grouped = {name for group in groups for name in group['ids']}
    return ''.join('>' + name + '\n' + sequence + '\n' for name, sequence in rows if name in grouped)


def read_chisq_table(text):
    """The rows of the service's chi-square table: ``(group labels, [{'position', 'statistic', 'p_value',
    'degrees_of_freedom', 'fewer_than_5', 'counts': {label: {residue: count}}}])``; the labels are the table's group columns."""
    lines = [line for line in text.splitlines() if line]
    header = lines[0].split('\t')
    if header[:5] != ['Position', 'Chi-square_value', 'P-value', 'Degrees_of_freedom', 'Fewer_5']:
        raise ValueError('metacats_chisq_table_header_unrecognised')
    labels, rows = header[5:], []
    for line in lines[1:]:
        cells = line.split('\t')
        cells += [''] * (len(header) - len(cells))
        rows.append({'position': int(cells[0].rstrip('*')), 'statistic': float(cells[1]), 'p_value': float(cells[2]),
                     'degrees_of_freedom': int(cells[3]), 'fewer_than_5': cells[4] == 'Y',
                     'counts': {label: {residue: int(count) for count, residue in _COUNT.findall(cell)}
                                for label, cell in zip(labels, cells[5:])}})
    return labels, rows


def grade(rows, groups, target_id, chisq_text, *, p_value):
    """The sheet of a MetaCATS result: the positions the service reports as significant at ``p_value`` (its own statistic
    and p-value; the table holds only those), for each the residue counts per group and the target's residue (read from the
    held alignment ``rows`` at the same column), and per group its VALUE: the mean over the significant positions of the
    fraction of the group's sequences that carry the target's residue there (0 to 1; a position where the target has a gap
    counts 0 for every group; a sequence of the group with a terminal gap there does not carry it). With no significant
    position the sheet says so and gives no value: the groups were measured not to differ, which places no candidate."""
    labels, table = read_chisq_table(chisq_text)
    if labels != [group['label'] for group in groups]:
        raise ValueError('metacats_result_groups_are_not_the_commissioned_groups')
    target = dict(rows)[target_id]
    columns = len(target)
    positions = []
    for row in table:
        residue = target[row['position'] - 1]
        carried = None if residue in '-#.' else residue
        fractions = {group['label']: 0.0 if carried is None else row['counts'][group['label']].get(carried, 0) / len(group['ids'])
                     for group in groups}
        positions.append({**row, 'target_residue': carried, 'fractions': fractions})
    values = ({group['label']: fmean(position['fractions'][group['label']] for position in positions) for group in groups}
              if positions else {})
    return {'schema': SCHEMA, 'application': 'MetaCATS', 'p_value': p_value, 'target': target_id, 'columns': columns,
            'sequence_count': sum(len(group['ids']) for group in groups), 'group_count': len(groups),
            'groups': [{'label': group['label'], 'product': group['product'], 'size': len(group['ids'])} for group in groups],
            'significant_positions': positions, 'significant_count': len(positions),
            'no_significant_position': not positions,
            'values': [{'label': group['label'], 'product': group['product'], 'value': values[group['label']]}
                       for group in groups] if positions else []}


__all__ = ['ALIGNMENT_FILE', 'CHISQ_FILE', 'GROUP_FILE', 'MC_FILE', 'MINIMUM_GROUPS', 'MINIMUM_GROUP_SIZE', 'P_VALUES',
           'SCHEMA', 'build_groups', 'derived_alignment', 'grade', 'group_file_text', 'parse_alignment',
           'read_chisq_table']
