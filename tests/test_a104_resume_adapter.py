"""Restart-adapter dispatch controls; no model, native tool or workflow."""
import ast
import asyncio

from tools.a104_resume_science import bind_method_super


def test_detached_async_method_preserves_original_super_dispatch():
    class Base:
        async def execute(self, name):
            return 'base:'+name
    class Original(Base):
        pass
    method = ast.parse('''async def execute(self, name):
    if name == 'special':
        return 'special'
    return await super().execute(name)
''').body[0]
    method = bind_method_super(method, 'Original')
    namespace = {'Original': Original}
    exec(compile(ast.Module(body=[method], type_ignores=[]), 'engineering_adapter', 'exec'), namespace)
    Original.execute = namespace['execute']
    instance = Original()
    assert asyncio.run(instance.execute('literature')) == 'base:literature'
    assert asyncio.run(instance.execute('special')) == 'special'
