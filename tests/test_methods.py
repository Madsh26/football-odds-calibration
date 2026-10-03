import unittest
import numpy as np
from scipy.optimize import brentq
from src.methods import remove_margin,scores,wilson,calibration_logistic,murphy
from src.inference import block_weights,extreme_gap,error_slope,holm,interval


class ProbabilityTests(unittest.TestCase):
    def test_symmetric_market(self):
        methods,k,z=remove_margin([[2.8,2.8,2.8]])
        for q in methods.values(): np.testing.assert_allclose(q,[[1/3]*3],atol=1e-10)
        self.assertAlmostEqual(k[0],np.log(1/3)/np.log(1/2.8),places=10)

    def test_independent_power_equation(self):
        odds=np.array([[2.1,3.4,3.75],[1.4,5.,8.]])
        methods,k,z=remove_margin(odds)
        for i,p in enumerate(1/odds):
            expected=brentq(lambda k: np.sum(p**k)-1,1,10)
            np.testing.assert_allclose(methods['power'][i],p**expected,atol=1e-10)
            # Original non-rationalized Shin expression independently checks stable version.
            S=p.sum();zz=z[i]
            original=(np.sqrt(zz**2+4*(1-zz)*p**2/S)-zz)/(2*(1-zz))
            np.testing.assert_allclose(methods['shin'][i],original,atol=1e-10)

    def test_invalid_markets_fail(self):
        for odds in [[[1,3,4]],[[float('inf'),3,4]],[[4,4,4]],[[1.01,1.5,100]]]:
            with self.assertRaises(ValueError): remove_margin(odds)

    def test_scoring_scale_and_order(self):
        q=np.array([[1/3]*3,[.8,.1,.1]]);y=np.array([[1,0,0],[1,0,0]])
        s=scores(q,y)
        np.testing.assert_allclose(s['brier'],[2/3,.06])
        np.testing.assert_allclose(s['rps'],[5/18,.025])
        np.testing.assert_allclose(s['log_loss'],[np.log(3),-np.log(.8)])

    def test_wilson_boundaries(self):
        for success in [0,50,100]:
            lo,hi=wilson(success,100)
            self.assertGreaterEqual(lo,-1e-12);self.assertLessEqual(hi,1+1e-12)
            self.assertLess(lo,hi)

    def test_murphy_residual_explicit(self):
        q=np.array([[.6,.2,.2],[.4,.3,.3],[.5,.2,.3],[.2,.3,.5]])
        y=np.eye(3)[[0,1,0,2]]
        m=murphy(q,y,2)
        self.assertAlmostEqual(m['brier'],m['reliability']-m['resolution']+m['uncertainty']+m['binning_residual'])


class InferenceTests(unittest.TestCase):
    def test_blocks_preserve_stratum_size(self):
        strata=[np.arange(6),np.arange(6,10)]
        for length in [1,3,20]:
            w=block_weights(10,strata,200,length,42)
            np.testing.assert_allclose(w[:,:6].sum(axis=1),6)
            np.testing.assert_allclose(w[:,6:].sum(axis=1),4)
            np.testing.assert_array_equal(w,block_weights(10,strata,200,length,42))

    def test_slope_matches_explicit_rows(self):
        q=np.array([[.6,.2,.2],[.4,.3,.3],[.5,.2,.3],[.2,.3,.5]])
        y=np.eye(3)[[0,1,0,2]];w=np.array([[2,1,0,3.]])
        ids=np.repeat(np.arange(4),w[0].astype(int));x=10*q[ids].ravel();e=100*(y[ids]-q[ids]).ravel()
        self.assertAlmostEqual(error_slope(q,y,w)[0],np.polyfit(x,e,1)[0])

    def test_fixed_extreme_membership(self):
        ref=np.array([[.7,.1,.2],[.1,.2,.7]]);q=ref+np.array([[-.05,.025,.025],[.025,.025,-.05]])
        y=np.array([[1,0,0],[0,0,1]]);w=np.ones((1,2))
        # q moves while membership remains defined by ref.
        expected=100*((y-q)[ref>.6].mean()-(y-q)[ref<.2].mean())
        self.assertAlmostEqual(extreme_gap(q,y,ref,w,.2,.6)[0],expected)

    def test_holm_known_values(self):
        np.testing.assert_allclose(holm([.01,.04,.03]),[.03,.06,.06])
        self.assertTrue(np.isnan(holm([np.nan,.01])[0]))

    def test_bootstrap_zero_effect(self):
        d=np.tile(np.linspace(-1,1,101),2)
        out=interval(0,d)
        self.assertEqual(out['p_boot'],1)


if __name__=='__main__': unittest.main()
