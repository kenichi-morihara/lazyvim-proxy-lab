"""An interrupted first fetch must be recoverable on the next run."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'editor/tools'))
from common import checkout

class CheckoutTests(unittest.TestCase):
    def test_empty_initialized_checkout_recovers_and_remains_pinned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, target = root / 'source', root / 'interrupted'
            def git(*args):
                return subprocess.check_output(['git', *map(str,args)], text=True, stderr=subprocess.DEVNULL).strip()
            git('init','-q',source)
            git('-C',source,'config','user.name','Checkout Test')
            git('-C',source,'config','user.email','checkout-test@example.invalid')
            (source/'file').write_text('pinned')
            git('-C',source,'add','file')
            git('-C',source,'commit','-qm','first')
            revision = git('-C',source,'rev-parse','HEAD')
            git('init','-q',target)
            git('-C',target,'remote','add','origin',source)
            checkout(str(source), revision, target)
            self.assertEqual((target/'file').read_text(),'pinned')
            (source/'file').write_text('newer')
            git('-C',source,'commit','-qam','second')
            checkout(str(source), revision, target)
            self.assertEqual(git('-C',target,'rev-parse','HEAD'),revision)

if __name__ == '__main__': unittest.main()
