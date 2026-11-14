"""Required original call-boundary custody; no whole action/native execution claim."""
import ast
import hashlib
import importlib
import json
from pathlib import Path
from types import MethodType
AX=__package__.rsplit('.tests',1)[0]
FIXTURE=Path(__file__).parent/'fixtures/literature_delivery_original'

def record():
    value=json.loads((FIXTURE/'manifest.json').read_text())
    assert value['version']=='a101_literature_original_call_boundaries_v1'
    assert len(value['homes'])==len(set(value['homes']))==14
    return value

def owner(home):return importlib.import_module(AX+'.'+home.replace('/','.')+'.task_decision')

def expression(home,method,selected):
    data=record();row=data['sources'][home];p=FIXTURE/row['file'];raw=p.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==row['sha256']
    tree=ast.parse(raw);cls,=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LiteratureTaskDecision']
    fn,=[n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name==method]
    original,=[n for n in ast.walk(fn) if isinstance(n,ast.Call) and ast.unparse(n.func)=='self.workflow.provider.complete']
    assert len(original.args)==5 and not original.keywords
    module=owner(home)
    if selected:
        actual=Path(module.__file__).read_bytes();ct=ast.parse(actual)
        cc,=[n for n in ct.body if isinstance(n,ast.ClassDef) and n.name==cls.name]
        cf,=[n for n in cc.body if isinstance(n,ast.AsyncFunctionDef) and n.name==method]
        call,=[n for n in ast.walk(cf) if isinstance(n,ast.Call) and ast.unparse(n.func)=='self.decision_completion()']
        assert [ast.dump(n,include_attributes=False) for n in call.args]==[ast.dump(n,include_attributes=False) for n in original.args]
        assert not call.keywords
    else:call=original
    # Execute exactly the original/selected call expression, with genuine defining globals.
    # This deliberately does not simulate the surrounding durable action or claim its coverage.
    code='async def boundary(self, instructions, context, schema, request):\n    return await '+ast.unparse(call)+'\n'
    namespace=dict(vars(module));exec(compile(code,str(p)+'::'+method+('::selected' if selected else '::original'),'exec'),namespace)
    return namespace['boundary'],module

def install_selector(subject,module):
    subject.decision_completion=MethodType(module.LiteratureTaskDecision.decision_completion,subject)
