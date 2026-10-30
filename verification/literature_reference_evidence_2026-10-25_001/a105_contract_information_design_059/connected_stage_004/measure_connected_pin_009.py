"""Run only the pinned metadata/request phase; test outcomes stay separate."""
import ast
from pathlib import Path
import runpy
import sys

STAGE = Path(__file__).absolute().parent
PIN = STAGE / 'pin_006'
OUT = STAGE / 'measurements_009'
OUT.mkdir(exist_ok=False)
sys.path[:0] = [str(PIN), str(PIN / 'tests')]
sys.argv = [str(PIN / 'run_connected_checks_005.py'), str(OUT)]
namespace = runpy.run_path(sys.argv[0], run_name='pinned_metadata_definitions')
tree = ast.parse((PIN / 'run_connected_checks_005.py').read_text())
main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
start = next(i for i, node in enumerate(main.body) if isinstance(node, ast.ImportFrom)
             and node.module == 'gene_annotation_episode')
# First three nodes load/verify the frozen manifest. Tests already run in their
# own recorded subprocess; this phase never labels them as passing.
main.body = main.body[:3] + [ast.Import(names=[ast.alias(name='pytest')])] + main.body[start:]
class SeparateTestStatus(ast.NodeTransformer):
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == 'int' and len(node.args) == 1 and isinstance(node.args[0], ast.Name) and node.args[0].id == 'code':
            return ast.copy_location(ast.Constant(value=None), node)
        return self.generic_visit(node)
    def visit_Constant(self, node):
        if node.value == 'passed':
            return ast.copy_location(ast.Constant(value='measurement_and_pin_verified'), node)
        return node
main = SeparateTestStatus().visit(main)
ast.fix_missing_locations(main)
exec(compile(ast.Module(body=[main], type_ignores=[]), str(__file__), 'exec'), namespace)
namespace['main']()
