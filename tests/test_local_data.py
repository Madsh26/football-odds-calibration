"""End-to-end controls on the supplied six CSVs; skip on a code-only checkout."""
import json
from pathlib import Path
import unittest
import numpy as np
from src.data import load_data

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(len(list((ROOT/'data/raw').glob('*.csv')))==6,'Raw data not present; run download_data.py')
class DataTests(unittest.TestCase):
    def test_complete_paired_sample(self):
        cfg=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
        m,y,cubes,params,base,manifest,coverage,exclusions=load_data(ROOT,cfg)
        self.assertEqual(len(m),2280);self.assertEqual(len(base),4560)
        self.assertEqual(m.match_id.nunique(),2280)
        self.assertTrue((coverage.eligible==380).all());self.assertEqual(len(exclusions),0)
        np.testing.assert_equal(y.sum(axis=1),np.ones(2280))
        for op in cubes:
            for q in cubes[op].values(): np.testing.assert_allclose(q.sum(axis=1),1,atol=1e-10)
        self.assertTrue((base.groupby('match_id').size()==2).all())
        self.assertEqual(len(manifest),6)

if __name__=='__main__': unittest.main()
