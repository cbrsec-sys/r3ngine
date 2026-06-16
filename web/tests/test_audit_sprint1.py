import ast
import os
import unittest


WORKFLOWS_FILE = os.path.join(
    os.path.dirname(__file__), '..', 'reNgine', 'temporal_workflows.py'
)


class TestAUD001AsyncioSleepInWorkflows(unittest.TestCase):
    """AUD-001: asyncio.sleep() must not appear inside workflow classes."""

    def test_no_asyncio_sleep_in_workflow_classes(self):
        with open(WORKFLOWS_FILE, encoding='utf-8-sig') as f:
            source = f.read()
        tree = ast.parse(source)

        workflow_class_bodies = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for decorator in node.decorator_list:
                    dec_name = ''
                    if isinstance(decorator, ast.Attribute):
                        dec_name = decorator.attr
                    elif isinstance(decorator, ast.Name):
                        dec_name = decorator.id
                    elif isinstance(decorator, ast.Call):
                        # Handle @workflow.defn(...) — decorator is a Call
                        func = decorator.func
                        if isinstance(func, ast.Attribute):
                            dec_name = func.attr
                        elif isinstance(func, ast.Name):
                            dec_name = func.id
                    if dec_name == 'defn':
                        workflow_class_bodies.append(node)

        violations = []
        for cls in workflow_class_bodies:
            for node in ast.walk(cls):
                if (
                    isinstance(node, ast.Await)
                    and isinstance(node.value, ast.Call)
                ):
                    func = node.value.func
                    if isinstance(func, ast.Attribute) and func.attr == 'sleep':
                        if isinstance(func.value, ast.Name) and func.value.id == 'asyncio':
                            violations.append(
                                f"asyncio.sleep() at line {node.lineno} in class {cls.name}"
                            )

        self.assertEqual(
            violations, [],
            f"Found asyncio.sleep() in workflow classes (AUD-001):\n" + "\n".join(violations)
        )
