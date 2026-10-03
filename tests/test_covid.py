"""Controles de la análisis de público local (público local y COVID-19)."""
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from src.covid import load_covid, _period

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))

class PeriodTests(unittest.TestCase):
    def test_period_boundaries(self):
        c=CFG['covid']
        self.assertEqual(_period('E0',pd.Timestamp('2020-03-09'),c),'pre')
        self.assertEqual(_period('SP1',pd.Timestamp('2020-03-10'),c),'closed')
        self.assertEqual(_period('E0',pd.Timestamp('2020-12-10'),c),'limited')
        self.assertEqual(_period('SP1',pd.Timestamp('2021-05-22'),c),'limited')
        self.assertEqual(_period('SP1',pd.Timestamp('2021-09-15'),c),'partial')
        self.assertEqual(_period('E0',pd.Timestamp('2021-09-15'),c),'post')
        self.assertEqual(_period('SP1',pd.Timestamp('2021-10-01'),c),'post')

@unittest.skipUnless(len(list((ROOT/'data/raw_covid').glob('*.csv')))==10,'Faltan los CSV de 2017/18-2021/22 en data/raw_covid')
class CovidDataTests(unittest.TestCase):
    def test_complete_seasons_and_measures(self):
        m,manifest,coverage=load_covid(ROOT,CFG)
        n_seasons=len(CFG['covid']['seasons'])
        self.assertEqual(len(m),2*n_seasons*380);self.assertEqual(len(manifest),2*n_seasons)
        # Pinnacle de cierre cubre todas las temporadas salvo un partido de LaLiga 2017/18.
        self.assertGreaterEqual(int(m.implied_PS.notna().sum()),len(m)-1)
        self.assertTrue(m.loc[m.season>='2019-20','implied_B365'].notna().all())
        self.assertTrue((m.groupby(['league','season']).size()==380).all())
        np.testing.assert_allclose(m.home_win+m.draw+m.away_win,1)
        # Puntos local − visitante es coherente con el resultado.
        self.assertTrue(set(np.unique(m.points_diff))<= {-3.,0.,3.})
        for op in CFG['operators']:
            v=m[f'implied_{op}'].dropna(); self.assertTrue(v.between(0,1).all())

class StrengthModelTests(unittest.TestCase):
    def test_strength_model_recovers_home_advantage(self):
        # Datos sintéticos: ventaja conocida por periodo y fuerzas aleatorias.
        import numpy as np, pandas as pd
        from src.covid import strength_adjusted
        rng=np.random.default_rng(1); teams=[f'T{i}' for i in range(6)]; rows=[]
        for season in ['A','B']:
            s={t:rng.normal() for t in teams}
            for h in teams:
                for a in teams:
                    if h!=a:
                        for period,ha in [('pre',.5),('closed',0.)]:
                            rows.append(dict(league='X',season=season,home=h,away=a,period=period,goal_diff=ha+s[h]-s[a]))
        m=pd.DataFrame(rows); W=np.ones((3,len(m)))
        out,(est,draws)=strength_adjusted(m,W,'X','goal_diff')
        self.assertAlmostEqual(est,-.5,places=8)

if __name__=='__main__': unittest.main()
