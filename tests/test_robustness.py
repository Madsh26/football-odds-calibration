import unittest
import numpy as np
from src.robustness import dyadic_meat, politis_white, week_weights, equivalence


class RobustnessTests(unittest.TestCase):
    def test_dyadic_meat_matches_brute_force(self):
        rng = np.random.default_rng(1)
        teams = np.array(list('ABCDEF'))
        pairs = [(h, a) for h in teams for a in teams if h != a]
        home = np.array([p[0] for p in pairs]); away = np.array([p[1] for p in pairs])
        S = rng.normal(size=(len(pairs), 2))
        brute = np.zeros((2, 2))
        for i in range(len(pairs)):
            for j in range(len(pairs)):
                if {home[i], away[i]} & {home[j], away[j]}:
                    brute += np.outer(S[i], S[j])
        self.assertTrue(np.allclose(dyadic_meat(S, home, away), brute))

    def test_politis_white_short_for_white_noise(self):
        x = np.random.default_rng(2).normal(size=380)
        self.assertLess(politis_white(x), 6)

    def test_week_weights_resample_whole_weeks(self):
        dates = np.array(['2024-08-10', '2024-08-11', '2024-08-17', '2024-08-18', '2024-08-24'], dtype='datetime64[ns]')
        W = week_weights(5, [np.arange(5)], dates, 50, 3)
        self.assertTrue(np.all(W[:, 0] == W[:, 1]) and np.all(W[:, 2] == W[:, 3]))

    def test_equivalence_classification(self):
        self.assertEqual(equivalence(dict(ci90_low=-.1, ci90_high=.2, ci_low=-.2, ci_high=.3), 1), 'equivalente')
        self.assertEqual(equivalence(dict(ci90_low=.1, ci90_high=2.0, ci_low=.05, ci_high=2.2), 1), 'diferente')
        self.assertEqual(equivalence(dict(ci90_low=-.5, ci90_high=1.5, ci_low=-.6, ci_high=1.7), 1), 'no concluyente')


if __name__ == '__main__':
    unittest.main()
