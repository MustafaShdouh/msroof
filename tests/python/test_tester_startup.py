"""A model-pin failure must leave an existing tester artifact intact."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.browser import build_tester_ui


class TesterStartupBuildTests(unittest.TestCase):
    def test_changed_model_does_not_replace_existing_page(self):
        with tempfile.TemporaryDirectory(prefix='masroof-startup-build-') as area:
            root=Path(area)
            builder=root/'tools/browser/build_tester_ui.py'
            builder.parent.mkdir(parents=True)
            target=builder.with_name('tester.html');target.write_text('existing tester',encoding='utf-8')
            model=root/'data/models/masroof_model.json';model.parent.mkdir(parents=True)
            model.write_text('{}',encoding='utf-8')
            contract=root/'config/contracts/core_validation_preflight_v1.json';contract.parent.mkdir(parents=True)
            contract.write_text(json.dumps(dict(runtime=dict(modelSha256='0'*64))),encoding='utf-8')
            with patch.object(build_tester_ui,'__file__',str(builder)):
                with self.assertRaisesRegex(ValueError,'pinned model'):build_tester_ui.build()
            self.assertEqual(target.read_text(encoding='utf-8'),'existing tester')
