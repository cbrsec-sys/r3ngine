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


class TestAUD005NucleiRetryPolicy(unittest.TestCase):
    """AUD-005: All RunNucleiActivity calls must have an explicit retry_policy."""

    def test_run_nuclei_activity_has_retry_policy(self):
        with open(WORKFLOWS_FILE, encoding='utf-8-sig') as f:
            source = f.read()
        tree = ast.parse(source)

        # Find all execute_activity calls with "RunNucleiActivity"
        missing_retry = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Await):
                continue
            call = node.value
            if not isinstance(call, ast.Call):
                continue
            # Check if this is workflow.execute_activity(...)
            func = call.func
            if not (isinstance(func, ast.Attribute) and func.attr == 'execute_activity'):
                continue
            # Check first arg is "RunNucleiActivity"
            if not call.args:
                continue
            first_arg = call.args[0]
            if not (isinstance(first_arg, ast.Constant) and first_arg.value == 'RunNucleiActivity'):
                continue
            # Check kwargs for retry_policy
            kwarg_names = {kw.arg for kw in call.keywords}
            if 'retry_policy' not in kwarg_names:
                missing_retry.append(f"line {node.lineno}")

        # Also assert we found at least one RunNucleiActivity call (guard against vacuous pass)
        all_nuclei_calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Await):
                continue
            call = node.value
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            if not (isinstance(func, ast.Attribute) and func.attr == 'execute_activity'):
                continue
            if not call.args:
                continue
            first_arg = call.args[0]
            if isinstance(first_arg, ast.Constant) and first_arg.value == 'RunNucleiActivity':
                all_nuclei_calls.append(f"line {node.lineno}")

        self.assertGreater(
            len(all_nuclei_calls), 0,
            "No RunNucleiActivity calls found in temporal_workflows.py — is the file correct?"
        )
        self.assertEqual(
            missing_retry, [],
            f"RunNucleiActivity called without retry_policy at: {missing_retry} (AUD-005)"
        )


class TestAUD006NucleiChildWorkflowRetryPolicy(unittest.TestCase):
    """AUD-006: NucleiPlannerWorkflow child invocations must have retry_policy."""

    def test_nuclei_planner_child_workflow_has_retry_policy(self):
        with open(WORKFLOWS_FILE, encoding='utf-8-sig') as f:
            source = f.read()
        tree = ast.parse(source)

        all_child_calls = []
        missing_retry = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Await):
                continue
            call = node.value
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            if not (isinstance(func, ast.Attribute) and func.attr == 'execute_child_workflow'):
                continue
            if not call.args:
                continue
            first_arg = call.args[0]
            if not (isinstance(first_arg, ast.Constant) and first_arg.value == 'NucleiPlannerWorkflow'):
                continue
            all_child_calls.append(f"line {node.lineno}")
            kwarg_names = {kw.arg for kw in call.keywords}
            if 'retry_policy' not in kwarg_names:
                missing_retry.append(f"line {node.lineno}")

        self.assertGreater(
            len(all_child_calls), 0,
            "No execute_child_workflow('NucleiPlannerWorkflow') calls found — is the file correct?"
        )
        self.assertEqual(
            missing_retry, [],
            f"NucleiPlannerWorkflow child invocation without retry_policy: {missing_retry} (AUD-006)"
        )
