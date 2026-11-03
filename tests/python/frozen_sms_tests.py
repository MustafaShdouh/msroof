"""Run every original historical test against its own checksum-bound source tree."""
import ast
import subprocess
import sys
import unittest

from tools.evaluation.replay_sms_research import frozen_workspace


def frozen_test_class(run_id, module_name, class_name):
    relative = module_name.replace(".", "/") + ".py"
    with frozen_workspace(run_id) as root:
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
    definition = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    names = [node.name for node in definition.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
    if not names:
        raise ValueError("Historical safeguards missing")

    class FrozenTests(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.workspace = frozen_workspace(run_id)
            cls.directory = cls.workspace.__enter__()

        @classmethod
        def tearDownClass(cls):
            cls.workspace.__exit__(None, None, None)

    def method(name):
        def original(self):
            result = subprocess.run([sys.executable, "-X", "utf8", "-m", "unittest", f"{module_name}.{class_name}.{name}"],
                                    cwd=self.directory, capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        original.__name__ = name
        return original

    for name in names:
        setattr(FrozenTests, name, method(name))
    FrozenTests.__name__ = class_name
    FrozenTests.__qualname__ = class_name
    FrozenTests.__module__ = module_name
    return FrozenTests
