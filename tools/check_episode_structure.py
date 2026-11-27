#!/usr/bin/env python3
"""The structure check: what one commit would bring into the tree, read as file names and source text, and the list of
its violations. It imports and runs nothing of the application (standard library and ``git`` only).

What the commit holds is read from git: with paths named after ``--`` (``git commit -m ... -- <paths>``) the working
tree's content of those paths against ``HEAD``; with none, the index against ``HEAD``. The checks, for the episode
folders and the library files the commit touches:

(a) every folder under ``root/`` on a changed path is an episode: it holds ``goal.py``, ``task.py``, ``credit.py``,
    ``yield_estimator.py``, ``episode.py`` and ``messages/`` with ``read_from_parent.py``, ``internal_summary.py`` and
    ``final_to_parent.py``, and ``msg_to_child.py`` and ``read_from_child.py`` exactly when it has child folders;
(b) no added line, and no added file's path, names a version (``_v<digit>``, ``legacy_``, ``old_``, ``deprecated_``,
    ``previous_``), outside the names of outside tools listed in ``OUTSIDE_NAMES``;
(c) no file under an episode folder imports from another episode's folder;
(d) is not a check: a library function is filed by what it is, which a name cannot tell this script (a library folder
    such as ``sequence_homology_evidence`` is a category of what its tools do);
(e) every changed path is inside the paths the session declared as its own;
(f) for an episode the declaration says is a copy of a reference episode: every name defined at the top level of each
    of its files that the reference's file of the same name does not define is printed, and is a violation unless the
    episode's design note lists it with a reason. An episode folder that is new in the commit must be declared a copy.

The declaration (``--declaration``) is a text file, one entry per line (``#`` starts a comment):

    own <path>                                  a file or a folder of the repository the session may change
    copy <episode folder> <reference episode folder> <design note>

A name is listed in a design note by a table row whose first cell is the file (as in the episode folder, for example
``messages/final_to_parent.py``), whose second cell is the name and whose last cell is the reason:

    | `task.py` | `GENES_TOOL` | `PROFILE_TOOL` | the tool of this head |

As the gate of a commit (``--hook-command``, the command a shell is about to run): a command that holds no
``git commit`` passes unread; a session with no declaration is not gated; a ``git commit`` must be the only command
(``cd <folder> &&`` may precede it) in a form whose content can be read before it runs, else it is refused.

Exit status: 0 no violation, 1 violations (listed on standard output), 2 the check could not be made."""
import argparse
import ast
import re
import shlex
import subprocess
import sys
from pathlib import Path, PurePosixPath

WORKFLOW = 'gene_annotation_episode/episodic_workflow/'
ROOT = WORKFLOW + 'root/'
LIBRARY = WORKFLOW + 'episode_support/'
ROOT_MODULE = ROOT.rstrip('/').replace('/', '.')
EPISODE_FILES = ('goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py')
MESSAGES = 'messages'
MESSAGE_FILES = ('read_from_parent.py', 'internal_summary.py', 'final_to_parent.py')
CHILD_MESSAGE_FILES = ('msg_to_child.py', 'read_from_child.py')
VERSION_NAME = re.compile(r'_v\d|(?<![A-Za-z0-9])(?:legacy|old|deprecated|previous)_', re.IGNORECASE)
# The names of outside tools, databases and file formats that carry the outside world's own version: exact text,
# each added with the owner's word and its reason beside it.
OUTSIDE_NAMES = ()
SEPARATORS = frozenset(';&|\n')
# The options of ``git commit`` that take the next word, and those whose commit this check cannot read beforehand.
COMMIT_VALUE_OPTIONS = {'-m', '-F', '-C', '-c', '-t', '--message', '--file', '--author', '--date', '--reuse-message',
                        '--reedit-message', '--template', '--cleanup', '--fixup', '--squash', '--trailer'}
COMMIT_UNREADABLE_OPTIONS = {'-a', '--all', '-i', '--include', '-p', '--patch', '--interactive', '--amend',
                             '--pathspec-from-file'}
GIT_VALUE_OPTIONS = {'-C', '-c', '--git-dir', '--work-tree', '--namespace', '--exec-path'}


class Unreadable(Exception):
    """The check could not be made."""


def git(directory, *arguments):
    done = subprocess.run(['git', '-C', str(directory), *arguments], capture_output=True)
    if done.returncode != 0:
        raise Unreadable('git ' + ' '.join(arguments) + ': ' + done.stderr.decode('utf-8', 'replace').strip())
    return done.stdout.decode('utf-8', 'replace')


class Commit:
    """What one commit would hold: the changed paths, the files of the tree it leaves and their text."""

    def __init__(self, directory, pathspecs):
        self.directory = directory
        self.repository = Path(git(directory, 'rev-parse', '--show-toplevel').strip())
        self.range = ['HEAD', '--', *pathspecs] if pathspecs else ['--cached']
        self.from_working_tree = bool(pathspecs)
        fields = git(directory, 'diff', '--no-renames', '--name-status', '-z', *self.range).split('\0')
        self.status = {path: status[0] for status, path in zip(fields[0::2], fields[1::2])}
        before = set(git(directory, 'ls-tree', '-r', '--name-only', '-z', 'HEAD').split('\0')) - {''}
        self.before = before
        self.files = (before | set(self.status)) - {path for path, status in self.status.items() if status == 'D'}

    def changed(self):
        return sorted(self.status)

    def text(self, path):
        """The text of ``path`` as the commit leaves it."""
        if path in self.status:
            if self.from_working_tree:
                return (self.repository / path).read_text(encoding='utf-8', errors='replace')
            return git(self.repository, 'show', ':' + path)
        return git(self.repository, 'show', 'HEAD:' + path)

    def added_lines(self, path):
        """The lines the commit adds to ``path``, each with its number in the file."""
        lines, number = [], 0
        for line in git(self.repository, 'diff', '--no-renames', '-U0', self.range[0], '--', path).splitlines():
            header = re.match(r'@@ -\d+(?:,\d+)? \+(\d+)', line)
            if header:
                number = int(header.group(1))
            elif number and line.startswith('+'):
                lines.append((number, line[1:]))
                number += 1
        return lines

    def children(self, folder):
        """The folders directly inside ``folder`` that hold a file of the tree the commit leaves."""
        prefix = folder + '/'
        return sorted({path[len(prefix):].split('/')[0] for path in self.files
                       if path.startswith(prefix) and '/' in path[len(prefix):]})


def read_declaration(path):
    own, copies = [], []
    for number, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        words = line.split('#')[0].split()
        if not words:
            continue
        if words[0] == 'own' and len(words) == 2:
            own.append(words[1].rstrip('/'))
        elif words[0] == 'copy' and len(words) == 4:
            copies.append(tuple(word.rstrip('/') for word in words[1:]))
        else:
            raise Unreadable('declaration line ' + str(number) + ' is neither "own <path>" nor "copy <episode folder> '
                             '<reference episode folder> <design note>"')
    return own, copies


def inside(path, folder):
    return path == folder or path.startswith(folder + '/')


def episode_folder(path):
    """The episode folder a file under ``root/`` belongs to, and the folders under ``root/`` on its path; ``None`` and
    the folders when the path runs through a folder inside ``messages``."""
    parts = PurePosixPath(path[len(ROOT):]).parts[:-1]
    folders = []
    for position, part in enumerate(parts):
        if part == MESSAGES:
            owner = folders[-1] if folders else ROOT.rstrip('/')
            return (owner if position == len(parts) - 1 else None), folders
        folders.append(ROOT + '/'.join(parts[:position + 1]))
    return (folders[-1] if folders else ROOT.rstrip('/')), folders


def check_episode_folders(commit):
    """(a)"""
    problems, seen = [], []
    for path in commit.changed():
        if not path.startswith(ROOT) or path not in commit.files:
            continue
        owner, folders = episode_folder(path)
        if owner is None:
            problems.append(('a', path, 'is in a folder inside ' + MESSAGES + '/, which holds only its files'))
        for folder in folders:
            if folder in seen:
                continue
            seen.append(folder)
            missing = [name for name in EPISODE_FILES if folder + '/' + name not in commit.files]
            missing += [MESSAGES + '/' + name for name in MESSAGE_FILES
                        if folder + '/' + MESSAGES + '/' + name not in commit.files]
            if missing:
                problems.append(('a', folder, 'is a folder under the root and not an episode: it lacks '
                                 + ', '.join(missing)))
            children = [name for name in commit.children(folder) if name != MESSAGES]
            held = [name for name in CHILD_MESSAGE_FILES if folder + '/' + MESSAGES + '/' + name in commit.files]
            if children and len(held) != len(CHILD_MESSAGE_FILES):
                problems.append(('a', folder, 'has child folders (' + ', '.join(children) + ') and lacks '
                                 + ', '.join(MESSAGES + '/' + name for name in CHILD_MESSAGE_FILES if name not in held)))
            if not children and held:
                problems.append(('a', folder, 'has no child folder and holds '
                                 + ', '.join(MESSAGES + '/' + name for name in held)))
    return problems


def version_names(text):
    for name in OUTSIDE_NAMES:
        text = text.replace(name, ' ')
    return sorted({found.group(0) for found in VERSION_NAME.finditer(text)})


def check_version_names(commit):
    """(b)"""
    problems = []
    for path in commit.changed():
        if not (path.startswith(ROOT) or path.startswith(LIBRARY)) or path not in commit.files:
            continue
        if commit.status[path] == 'A' and version_names(path):
            problems.append(('b', path, 'the path of an added file names a version: ' + ', '.join(version_names(path))))
        for number, line in commit.added_lines(path):
            if version_names(line):
                problems.append(('b', path + ':' + str(number), 'an added line names a version ('
                                 + ', '.join(version_names(line)) + '): ' + line.strip()[:160]))
    return problems


def imported_modules(path, tree):
    """Every module an import statement of the file names, as a dotted path from the top of the repository (a name
    imported ``from`` a module is given too, as it may be a module of that package)."""
    package = PurePosixPath(path).parts[:-1]
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = list(package[:len(package) - (node.level - 1)]) if node.level else []
            module = '.'.join(base + ([node.module] if node.module else []))
            found.append((node.lineno, module))
            found += [(node.lineno, module + '.' + alias.name) for alias in node.names]
    return found


def check_imports(commit):
    """(c)"""
    problems = []
    own_names = {name[:-3] for name in EPISODE_FILES} | {MESSAGES}
    for path in commit.changed():
        if not path.startswith(ROOT) or not path.endswith('.py') or path not in commit.files:
            continue
        owner, _ = episode_folder(path)
        if owner is None:
            continue
        try:
            tree = ast.parse(commit.text(path))
        except SyntaxError as error:
            problems.append(('c', path, 'cannot be read as Python: ' + str(error)))
            continue
        own_module = owner.replace('/', '.')
        children = [name for name in commit.children(owner) if name != MESSAGES]
        reported = set()
        for line, module in imported_modules(path, tree):
            if not inside(module.replace('.', '/'), ROOT_MODULE.replace('.', '/')) or line in reported:
                continue
            rest = module[len(own_module):].strip('.').split('.') if inside(
                module.replace('.', '/'), own_module.replace('.', '/')) else None
            if rest is None or (rest[0] in children and rest[0] not in own_names):
                reported.add(line)
                problems.append(('c', path + ':' + str(line), 'imports from another episode\'s folder: ' + module))
    return problems


def check_own_paths(commit, own):
    """(e)"""
    return [('e', path, 'is outside the paths this session declared as its own')
            for path in commit.changed() if not any(inside(path, entry) for entry in own)]


def top_level_names(text):
    names = []
    for node in ast.parse(text).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                names += [item.id for item in ast.walk(target) if isinstance(item, ast.Name)]
    return names


def listed_names(note_text):
    """``{(file, name)}`` of the table rows of a design note that give a name with a reason."""
    listed = set()
    for line in note_text.splitlines():
        if line.lstrip().startswith('|'):
            cells = [cell.strip().strip('`') for cell in line.strip().strip('|').split('|')]
            if len(cells) >= 3 and cells[-1].strip('-: '):
                listed.add((cells[0], cells[1]))
    return listed


def check_copies(commit, copies):
    """(f)"""
    problems = []
    declared = [new for new, _, _ in copies]
    for path in commit.changed():
        if path.startswith(ROOT) and path in commit.files:
            for folder in episode_folder(path)[1]:
                new = not any(inside(before, folder) for before in commit.before)
                if new and folder not in declared and ('f', folder) not in [(p[0], p[1]) for p in problems]:
                    problems.append(('f', folder, 'is an episode folder new in this commit and the declaration names '
                                                  'no reference episode it is a copy of'))
    for new, reference, note in copies:
        if not any(inside(path, new) for path in commit.changed()):
            continue
        if note not in commit.files:
            problems.append(('f', new, 'its design note is not in the tree: ' + note))
            continue
        listed = listed_names(commit.text(note))
        own = [path for path in sorted(commit.files) if path.endswith('.py') and inside(path, new)
               and episode_folder(path)[0] == new]
        for path in own:
            relative = path[len(new) + 1:]
            try:
                names = top_level_names(commit.text(path))
                counterpart = reference + '/' + relative
                known = set(top_level_names(commit.text(counterpart))) if counterpart in commit.files else set()
            except SyntaxError as error:
                problems.append(('f', path, 'cannot be read as Python: ' + str(error)))
                continue
            for name in dict.fromkeys(names):
                if name not in known and (relative, name) not in listed:
                    problems.append(('f', path, 'defines ' + name + ', which ' + reference + '/' + relative
                                     + ' does not define and ' + note + ' does not list with a reason'))
    return problems


def check(commit, own, copies):
    return (check_episode_folders(commit) + check_version_names(commit) + check_imports(commit)
            + check_own_paths(commit, own) + check_copies(commit, copies))


def commit_of_command(command, directory):
    """``None`` when the shell command holds no ``git commit``; else ``(directory, pathspecs)`` of the one it holds.
    Raises ``Unreadable`` for a commit this check cannot read before it runs."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars='();<>|&\n')
    lexer.whitespace = ' \t\r'
    lexer.whitespace_split = True
    try:
        words = list(lexer)
    except ValueError as error:
        if re.search(r'\bgit\b[^|;&\n]*\bcommit\b', command):
            raise Unreadable('the command could not be read (' + str(error) + '): give the message with -F <file>')
        return None
    segments, segment = [], []
    for word in words:
        if set(word) <= SEPARATORS:
            segments.append(segment)
            segment = []
        else:
            segment.append(word)
    segments = [found for found in [*segments, segment] if found]
    found = None
    for position, segment in enumerate(segments):
        gits = [index for index, word in enumerate(segment) if word == 'git' or word.endswith('/git')]
        arguments = segment[gits[0] + 1:] if gits else []
        while arguments and arguments[0].startswith('-'):
            if arguments[0] == '-C' and len(arguments) > 1:
                directory = Path(directory, arguments[1])
            arguments = arguments[2 if arguments[0] in GIT_VALUE_OPTIONS else 1:]
        if arguments[:1] == ['commit']:
            if found is not None:
                raise Unreadable('two commits in one command: run each git commit as its own command')
            found = (position, arguments[1:], directory)
        elif found is None and segment[0] == 'cd' and len(segment) == 2:
            directory = Path(directory, segment[1])
        elif any(re.search(r'\bgit\b.*\bcommit\b', word, re.DOTALL) for word in segment):
            raise Unreadable('a git commit inside a quoted command cannot be read: run git commit as its own command')
    if found is None:
        return None
    position, arguments, directory = found
    if position != len(segments) - 1 or any(segment[0] != 'cd' or len(segment) != 2 for segment in segments[:position]):
        raise Unreadable('git commit must be the only command (cd <folder> && may precede it): what else the command '
                         'runs could change what is committed after this check')
    pathspecs, index = [], 0
    while index < len(arguments):
        word = arguments[index]
        index += 1
        if word == '--':
            pathspecs += arguments[index:]
            break
        if word.startswith('--'):
            name = word.split('=')[0]
            if name in COMMIT_UNREADABLE_OPTIONS:
                raise Unreadable('git commit ' + name + ' cannot be read before it runs: stage or name exact paths')
            index += 1 if name in COMMIT_VALUE_OPTIONS and '=' not in word else 0
        elif word.startswith('-') and len(word) > 1:
            for place, letter in enumerate(word[1:], 1):
                if '-' + letter in COMMIT_UNREADABLE_OPTIONS:
                    raise Unreadable('git commit -' + letter + ' cannot be read before it runs: stage or name exact paths')
                if '-' + letter in COMMIT_VALUE_OPTIONS:
                    index += 1 if place == len(word) - 1 else 0
                    break
        else:
            pathspecs.append(word)
    return directory, pathspecs


def main():
    parser = argparse.ArgumentParser(description='The structure check of one commit.')
    parser.add_argument('--declaration', required=True, help='the session\'s declaration file')
    parser.add_argument('--directory', default='.', help='the folder the commit is made from')
    parser.add_argument('--hook-command', help='the shell command about to run: gate it if it is a git commit')
    parser.add_argument('pathspecs', nargs='*', help='the paths named after -- in git commit (none: the index)')
    arguments = parser.parse_args()
    try:
        directory, pathspecs = Path(arguments.directory), arguments.pathspecs
        if arguments.hook_command is not None:
            found = commit_of_command(arguments.hook_command, directory)
            if found is None:
                return 0
            if not Path(arguments.declaration).is_file():
                print('structure check: this session has no declaration (' + arguments.declaration + '); not gated')
                return 0
            directory, pathspecs = found
        own, copies = read_declaration(arguments.declaration)
        commit = Commit(directory, pathspecs)
        problems = check(commit, own, copies)
    except (Unreadable, OSError) as error:
        print('structure check could not be made: ' + str(error))
        return 2
    print('structure check: ' + str(len(commit.changed())) + ' changed path(s), ' + str(len(problems)) + ' violation(s)'
          + ('' if problems else ': passes'))
    for letter, where, what in problems:
        print('(' + letter + ') ' + where + ': ' + what)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
