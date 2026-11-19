"""Measure the per-episode files of the nine axis head trees at the last commit (read-only).

Reads only ``gene_annotation_episode/episodic_workflow/root/<axis>/<role>/**`` at HEAD (``git cat-file``),
non-test ``.py`` files other than ``__init__.py``, and the working tree's directory listing. Writes the tables
CARRY_OVER_GUIDE.md cites into the directory given as the one argument:

- ``file_names.tsv``: each per-episode file name, its copies, different contents (after replacing the file's
  own folder names and axis id), axes, the kinds of episode folder that held it, and its uses of each family
  of old-runner names;
- ``old_runner_names.tsv``: every distinct old-runner name used, its uses and the file names using it;
- ``per_file_name.tsv``: the old-runner names each file name used;
- ``episode_folders.tsv``: every episode folder at HEAD and what the working tree holds there now;
- ``axis_shared_modules.tsv``: every module outside the episode's own folder that the old files imported,
  and where a module of that name is in the working tree now;
- ``episode_bases.tsv``: where the base classes of each old ``episode.py`` class came from.
"""
import ast
import hashlib
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

AXES = {'a101': 'sequence_homology_evidence', 'a102': 'structural_homology_evidence', 'a103': 'gene_context_evidence',
        'a104': 'evolutionary_history_evidence', 'a105': 'experimental_activity_evidence', 'a106': 'perturbation_evidence',
        'a107': 'partner_presence_evidence', 'a108': 'sample_context_evidence', 'a110': 'biochemical_feasibility_evidence'}
ROOT = 'gene_annotation_episode/episodic_workflow/root/'
PKG = 'gene_annotation_episode.episodic_workflow.root.'
SUPPORT = Path('gene_annotation_episode/episodic_workflow/episode_support')
# Attributes of the old runner's BindingContext, of the old task source seen from outside, and the state the
# old task source kept for the old runner.
CONTEXT = {'role', 'assignment', 'episode_id', 'scope', 'run_id', 'received_record_refs', 'path', 'request', 'as_record'}
SOURCE = {'episode_id', 'scope', 'path', 'last_outcome_index', 'feedback', 'last_outcome', 'report_values',
          'interpret_schema'}
TASK_STATE = {'episode_id', 'feedback', 'last_outcome', 'last_outcome_index', 'request', 'report_values', 'report_basis',
              'scope', 'calls', 'path', 'interpret_schema', 'workflow', '_restored', '_restored_source_state',
              '_unfinished_own_actions', '_inprocess_replay_ready', '_model_snapshot', '_source_revision',
              '_latest_effect_index', '_execution_context', 'record_effect', 'checkpoint', '_presented_conversation_key',
              '_selection_view', 'restore_checkpoint', 'restore', '_suspension_condition', '_delivery_resolution_ref',
              'call'}
TASK_FILES = re.compile(r'^(task|decision_|report_delivery|saved_decision|action_|call\.py|waiting|instructions)')
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)


def blobs(paths):
    process = subprocess.Popen(['git', 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    result = {}
    for path in paths:
        process.stdin.write(('HEAD:' + path + '\n').encode())
        process.stdin.flush()
        size = int(process.stdout.readline().split()[2])
        result[path] = process.stdout.read(size).decode('utf-8', 'replace')
        process.stdout.read(1)
    process.stdin.close()
    return result


def normal(path, text, axis):
    words = set(path[len(ROOT):].split('/')[:-1]) | {axis, axis.upper()}
    for word in sorted(words, key=len, reverse=True):
        text = re.sub(r'(?<![A-Za-z0-9])' + re.escape(word) + r'(?![A-Za-z0-9])', '<HOME>', text)
    return hashlib.sha1(re.sub(r'<HOME>(?:[./_]<HOME>)+', '<HOME>', text).encode()).hexdigest()


def chain(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return list(reversed(parts))
    return None


def family(token):
    for prefix, name in (('workflow.', 'workflow'), ('_live_original', 'old_runtime_module'), ('context.', 'binding_context'),
                         ('source.', 'task_source_from_outside'), ('services.', 'services'), ('task_source.', 'task_source_state'),
                         ('import axis-shared:', 'axis_shared_import'), ('import old-root:', 'old_root_import'),
                         ('import ancestor-folder:', 'ancestor_folder_import'),
                         ('import other-episode-folder:', 'other_episode_folder_import'),
                         ('import package:', 'package_import')):
        if token.startswith(prefix):
            return name
    raise ValueError(token)


listing = subprocess.run(['git', 'ls-tree', '-r', '--name-only', 'HEAD', ROOT], capture_output=True, text=True,
                         check=True).stdout.split('\n')
paths = []
for axis, role in AXES.items():
    prefix = ROOT + axis + '/' + role + '/'
    paths += [(axis, role, p) for p in listing if p.startswith(prefix) and p.endswith('.py') and '/tests/' not in p
              and not p.endswith('__init__.py')]
content = blobs([p for _, _, p in paths])
episode_folders = sorted({p.rsplit('/', 1)[0] for _, _, p in paths if p.endswith('/episode.py')})
by_folder = defaultdict(list)
for _, _, path in paths:
    by_folder[path.rsplit('/', 1)[0]].append(path)

uses = defaultdict(Counter)        # file name -> token -> uses
files_using = defaultdict(lambda: defaultdict(set))
modules = defaultdict(lambda: [0, set(), Counter()])   # (axis, kind, module) -> uses, names, file names
bases = []
copies, variants, kinds, axes_of = Counter(), defaultdict(set), defaultdict(Counter), defaultdict(set)
for axis, role, path in paths:
    name = path.rsplit('/', 1)[1]
    folder = path.rsplit('/', 1)[0]
    copies[name] += 1
    variants[name].add(normal(path, content[path], axis))
    kinds[name][folder.rsplit('/', 1)[1]] += 1
    axes_of[name].add(axis)
    tree = ast.parse(content[path])
    package = folder.replace('/', '.')
    head = PKG + axis + '.' + role
    tokens, origin, seen = Counter(), {}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if node.level:
                base = package.split('.')
                base = base[:len(base) - (node.level - 1)]
                target = '.'.join(base + ([module] if module else []))
            else:
                target = module
            if target == package or target.startswith(package + '.'):
                inside = target[len(package):].lstrip('.')
                kind = 'own-folder' if '.' not in inside else 'other-episode-folder'   # a sub-package is a child episode
            elif target == head or target.startswith(head + '.'):
                holder = target.rsplit('.', 1)[0]
                kind = 'ancestor-folder' if (package + '.').startswith(holder + '.') else 'other-episode-folder'
            elif target.startswith(PKG + axis + '.') or target == PKG + axis:
                kind = 'axis-shared'
            elif target.startswith(PKG):
                kind = 'old-root'
            elif target.startswith('gene_annotation_episode'):
                kind = 'package'
            else:
                kind = 'outside'
            for alias in node.names:
                origin[alias.asname or alias.name] = kind
                if kind in ('own-folder', 'outside'):
                    continue
                short = {'axis-shared': target[len(PKG + axis):].lstrip('.'), 'old-root': target[len(PKG):],
                         'package': target[len('gene_annotation_episode'):].lstrip('.')}.get(kind, target.rsplit('.', 1)[1])
                tokens['import ' + kind + ':' + short + ':' + alias.name] += 1
                entry = modules[(axis, kind, short)]
                entry[0] += 1
                entry[1].add(alias.name)
                entry[2][name] += 1
        elif isinstance(node, ast.Attribute) and id(node) not in seen:
            parts = chain(node)
            sub = node
            while isinstance(sub, ast.Attribute):
                seen.add(id(sub))
                sub = sub.value
            if not parts or len(parts) < 2:
                continue
            if 'workflow' in parts[:-1]:
                index = parts.index('workflow')
                tokens['workflow.' + '.'.join(parts[index + 1:index + 3])] += 1
            elif parts[0].startswith('_live_original'):
                tokens[parts[0] + '.' + parts[1]] += 1
            elif parts[0] in ('context', 'parent', 'receiver', 'binding_context') and parts[1] in CONTEXT:
                tokens['context.' + parts[1]] += 1
            elif parts[:2] == ['self', 'services'] and len(parts) > 2:
                tokens['services.' + parts[2]] += 1
            elif parts[0] == 'services':
                tokens['services.' + parts[1]] += 1
            elif parts[0] == 'source' and parts[1] in SOURCE:
                tokens['source.' + parts[1]] += 1
            elif parts[0] == 'self' and parts[1] in TASK_STATE and TASK_FILES.match(name):
                tokens['task_source.' + parts[1]] += 1
    for token, count in tokens.items():
        uses[name][token] += count
        files_using[name][token].add(path)
    if name == 'episode.py':
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and any(
                    isinstance(item, ast.Assign) and any(getattr(t, 'id', None) == 'binding_path' for t in item.targets)
                    for item in node.body):
                found = Counter()
                for base in node.bases:
                    parts = chain(base) if isinstance(base, ast.Attribute) else [getattr(base, 'id', '?')]
                    found[origin.get(parts[0], 'defined-in-episode.py' if any(
                        isinstance(other, ast.ClassDef) and other.name == parts[0] for other in tree.body) else 'unresolved')] += 1
                bases.append((axis, folder[len(ROOT):], node.name, len(node.bases), found))

total, total_names = Counter(), defaultdict(Counter)
for name, tokens in uses.items():
    for token, count in tokens.items():
        total[token] += count
        total_names[token][name] += count
families = sorted({family(token) for token in total})
with open(out / 'file_names.tsv', 'w') as handle:
    handle.write('file_name\tcopies\tdifferent_contents\taxes\tfolder_kinds\t' + '\t'.join(families) + '\n')
    for name, count in copies.most_common():
        per_family = Counter()
        for token, used in uses[name].items():
            per_family[family(token)] += used
        handle.write('\t'.join([name, str(count), str(len(variants[name])), ','.join(sorted(axes_of[name])),
                                ' '.join(k + ':' + str(v) for k, v in kinds[name].most_common()),
                                *(str(per_family[f]) for f in families)]) + '\n')
with open(out / 'old_runner_names.tsv', 'w') as handle:
    handle.write('family\tname\tuses\tfile_names_using\tfile_names\n')
    for token, count in sorted(total.items(), key=lambda item: (family(item[0]), -item[1], item[0])):
        handle.write('\t'.join((family(token), token, str(count), str(len(total_names[token])), ' '.join(
            n[:-3] + ':' + str(c) for n, c in total_names[token].most_common()))) + '\n')
with open(out / 'per_file_name.tsv', 'w') as handle:
    handle.write('file_name\tcopies\tfamily\tname\tuses\tfiles_using\n')
    for name, count in copies.most_common():
        merged, merged_files = Counter(), defaultdict(set)
        for token, used in uses[name].items():
            fam = family(token)
            key = token if not fam.endswith('_import') or fam == 'old_root_import' else token.rsplit(':', 1)[0]
            merged[key] += used
            merged_files[key] |= files_using[name][token]
        for key, used in merged.most_common():
            handle.write('\t'.join((name, str(count), family(key + ':x' if key.startswith('import') and key.count(':') == 1
                                                             else key), key, str(used), str(len(merged_files[key])))) + '\n')
with open(out / 'episode_folders.tsv', 'w') as handle:
    handle.write('axis\tepisode_folder\thead_files\tfolder_now\tepisode_py_now\tpy_files_now\thead_file_names_still_present\n')
    for folder in episode_folders:
        now = Path(folder)
        present = [p for p in now.glob('*.py') if p.name != '__init__.py'] if now.is_dir() else []
        handle.write('\t'.join((folder[len(ROOT):].split('/')[0], folder[len(ROOT):], str(len(by_folder[folder])),
                                'yes' if now.is_dir() else 'no', 'yes' if (now / 'episode.py').is_file() else 'no',
                                str(len(present)), str(sum(1 for p in by_folder[folder] if Path(p).is_file())))) + '\n')
support = defaultdict(list)
for path in SUPPORT.rglob('*.py'):
    if '/tests/' not in str(path):
        support[path.stem].append(str(path.relative_to(SUPPORT.parent)))
with open(out / 'axis_shared_modules.tsv', 'w') as handle:
    handle.write('axis\torigin\tmodule\tuses\tnames_imported\tfile_names_using\tmodule_of_that_name_now\n')
    for (axis, kind, module), (count, names, where) in sorted(modules.items(), key=lambda item: (item[0][0], item[0][1], -item[1][0])):
        stem = module.rsplit('.', 1)[-1] if module else ''
        role = AXES[axis]
        found = [p for p in support.get(stem, ()) if '/' + role + '/' in p] or [p for p in support.get(stem, ())
                                                                              if not any('/' + r + '/' in p for r in AXES.values())]
        top = Path('gene_annotation_episode') / (stem + '.py')
        if kind == 'package' and top.is_file():
            found = [str(top)]
        handle.write('\t'.join((axis, kind, module or '(the axis package)', str(count), str(len(names)),
                                ' '.join(n[:-3] + ':' + str(c) for n, c in where.most_common(6)),
                                '; '.join(found[:3]) if found and kind in ('axis-shared', 'package') else
                                ('' if kind not in ('axis-shared', 'package') else 'none'))) + '\n')
with open(out / 'episode_bases.tsv', 'w') as handle:
    handle.write('axis\tepisode_folder\tclass\tbases\tbase_origins\n')
    for axis, folder, name, count, found in bases:
        handle.write('\t'.join((axis, folder, name, str(count), ' '.join(k + ':' + str(v) for k, v in sorted(found.items())))) + '\n')
origins = Counter()
for _, _, _, _, found in bases:
    origins.update(found)
print('files', len(paths), 'file names', len(copies), 'episode folders', len(episode_folders), 'old-runner names', len(total))
print('binding classes', len(bases), 'base origins', dict(origins))
print('families', {f: sum(c for t, c in total.items() if family(t) == f) for f in families})
