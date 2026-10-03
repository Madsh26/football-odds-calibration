"""Independent reconciliation of executed outputs, skipped before first run."""
from pathlib import Path
import json
import re
import unittest
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless((ROOT/'data/processed/analytic.csv').exists(),'Execute run_all.py to validate result exports')
class ResultTests(unittest.TestCase):
    def test_exported_scores_reconcile(self):
        base=pd.read_csv(ROOT/'data/processed/analytic.csv')
        summary=pd.read_csv(ROOT/'reports/tables/scores.csv')
        for (league,op),d in base.groupby(['league','operator']):
            y=d[['y_H','y_D','y_A']].to_numpy()
            for method in ['proportional','power','additive','shin']:
                q=d[[method+'_'+r for r in 'HDA']].to_numpy()
                brier=np.mean(np.sum((q-y)**2,axis=1))
                rps=np.mean(((q[:,0]-y[:,0])**2+((q[:,0]+q[:,1])-(y[:,0]+y[:,1]))**2)/2)
                row=summary.query('league==@league and operator==@op and method==@method and season=="all"').iloc[0]
                self.assertAlmostEqual(row.brier,brier,places=10);self.assertAlmostEqual(row.rps,rps,places=10)

    def test_method_contrast_cancels_observed_result(self):
        base=pd.read_csv(ROOT/'data/processed/analytic.csv')
        effects=pd.read_csv(ROOT/'reports/tables/method_differences.csv')
        for (league,op),d in base.groupby(['league','operator']):
            ref=d[['proportional_'+r for r in 'HDA']].to_numpy()
            power=d[['power_'+r for r in 'HDA']].to_numpy()
            adjustment=100*(ref-power)
            effect=adjustment[ref>.6].mean()-adjustment[ref<.2].mean()
            row=effects.query('league==@league and operator==@op and season=="all" and metric=="extreme_gap" and comparison=="power minus proportional"').iloc[0]
            self.assertAlmostEqual(row.estimate,effect,places=10)

    def test_intervals_and_adjustments(self):
        for name in ['bias','extremes','method_differences','operator_differences','league_differences','season_differences','outcome_calibration']:
            d=pd.read_csv(ROOT/f'reports/tables/{name}.csv')
            self.assertTrue(np.isfinite(d[['estimate','ci_low','ci_high','p_boot','p_holm']]).all().all(),name)
            self.assertTrue((d.ci_low<=d.ci_high).all(),name)
            self.assertTrue(d.p_boot.between(0,1).all(),name)
            self.assertTrue((d.p_holm+1e-10>=d.p_boot).all(),name)
            meta=ROOT/'reports/run_metadata.json'
            expected=json.loads(meta.read_text(encoding='utf-8'))['config']['bootstrap_reps'] if meta.exists() else 2000
            self.assertTrue((d.bootstrap_valid==expected).all(),name)

    def test_html_local_references_exist(self):
        report=ROOT/'reports/index.html'
        s=report.read_text(encoding='utf-8')
        for link in re.findall(r'href="([^"]+)"',s):
            if link.startswith(('http','#')): continue
            self.assertTrue((report.parent/link).exists(),link)
        # 9 figuras del análisis principal + 4 de la análisis de público local (COVID).
        self.assertEqual(s.count('data:image/png;base64,'),13)

if __name__=='__main__': unittest.main()
