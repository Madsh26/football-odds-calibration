"""Offline checks for historical downloads and source version protection."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('downloader', ROOT / 'download_data.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Response:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self):
        return b'Div,Date,HomeTeam,AwayTeam,FTR,FTHG,FTAG,B365CH,PSCH\n'


class DownloadTests(unittest.TestCase):
    def test_all_sixteen_files_and_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'config.json').write_text((ROOT / 'config.json').read_text(encoding='utf-8'), encoding='utf-8')
            with patch.object(module, '__file__', str(root / 'download_data.py')), patch.object(module, 'urlopen', return_value=Response()) as fetch:
                module.main()
                self.assertEqual(fetch.call_count, 16)
                self.assertEqual(len(list((root / 'data/raw').glob('*.csv'))), 6)
                self.assertEqual(len(list((root / 'data/raw_covid').glob('*.csv'))), 10)
                module.main()
                self.assertEqual(fetch.call_count, 16)

    def test_changed_snapshot_is_not_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            (root / 'config.json').write_text(json.dumps({'leagues': {'E0':'Premier'}, 'seasons':['2022-23']}))
            (root / 'data/source_snapshot.csv').write_text('file,sha256\nE0_2022-23.csv,incorrect\n')
            with patch.object(module, '__file__', str(root / 'download_data.py')), patch.object(module, 'urlopen', return_value=Response()):
                with self.assertRaisesRegex(ValueError, 'snapshot'):
                    module.main()
            self.assertFalse((root / 'data/raw/E0_2022-23.csv').exists())
