"""Executable discovery must honor explicit configuration and reject bad paths."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.node_runtime import node_executable


class NodeRuntimeTests(unittest.TestCase):
    def test_configured_executable_precedes_path(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "node.exe"
            binary.write_bytes(b"fixture")
            with patch.dict(os.environ, {"MASROOF_NODE": str(binary)}), patch("tools.node_runtime.shutil.which") as find:
                self.assertEqual(node_executable(), str(binary.resolve()))
                find.assert_not_called()

    def test_invalid_configuration_is_not_silently_ignored(self):
        with patch.dict(os.environ, {"MASROOF_NODE": "missing-node-binary"}), patch("tools.node_runtime.shutil.which") as find:
            with self.assertRaises(FileNotFoundError):
                node_executable()
            find.assert_not_called()

    def test_path_executable_is_used_without_an_override(self):
        with patch.dict(os.environ, {"MASROOF_NODE": ""}), patch("tools.node_runtime.shutil.which", return_value="discovered-node"):
            self.assertEqual(node_executable(), "discovered-node")
