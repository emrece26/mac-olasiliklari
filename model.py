"""Zaman ağırlıklı Dixon-Coles modeli.

Her takımın bir hücum (att) ve savunma (def) gücü vardır:
    log(ev sahibi gol beklentisi)   = mu + home + att[ev] + def[dep]
    log(deplasman gol beklentisi)   = mu +        att[dep] + def[ev]
Goller Poisson dağılımlıdır; düşük skorlu sonuçlar (0-0, 1-0, 0-1, 1-1) için
Dixon-Coles düzeltmesi (rho) uygulanır. Eski maçlar exp(-xi * gün) ile
ağırlıklandırılır, böylece güncel form daha çok etkiler.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson

MAX_GOALS = 10


class DixonColes:
    def __init__(self, xi=0.002, reg=1.0):
        self.xi = xi    # zaman azalma katsayısı (gün başına)
        self.reg = reg  # L2 düzenleme (az maçı olan takımları ortalamaya çeker)

    def fit(self, home, away, hg, ag, days_ago, teams=None, prior=None):
        """prior: {takım: (att_önsel, def_önsel)} — az verili takımlar bu değere çekilir."""
        self.teams = sorted(set(home) | set(away)) if teams is None else list(teams)
        idx = {t: i for i, t in enumerate(self.teams)}
        h = np.array([idx[t] for t in home])
        a = np.array([idx[t] for t in away])
        x = np.asarray(hg, float)
        y = np.asarray(ag, float)
        w = np.exp(-self.xi * np.asarray(days_ago, float))
        n = len(self.teams)
        prior = prior or {}
        pa = np.array([prior.get(t, (0.0, 0.0))[0] for t in self.teams])
        pd_ = np.array([prior.get(t, (0.0, 0.0))[1] for t in self.teams])

        x0, y0 = (x == 0), (y == 0)
        x1, y1 = (x == 1), (y == 1)
        m00, m01, m10, m11 = x0 & y0, x0 & y1, x1 & y0, x1 & y1

        def nll(p):
            mu, home_adv, rho = p[0], p[1], p[2]
            att, dfn = p[3:3 + n], p[3 + n:]
            e1 = mu + home_adv + att[h] + dfn[a]
            e2 = mu + att[a] + dfn[h]
            lam, nu = np.exp(e1), np.exp(e2)
            tau = np.ones_like(lam)
            tau[m00] = 1 - lam[m00] * nu[m00] * rho
            tau[m01] = 1 + lam[m01] * rho
            tau[m10] = 1 + nu[m10] * rho
            tau[m11] = 1 - rho
            tau = np.maximum(tau, 1e-10)
            ll = np.log(tau) + x * e1 - lam + y * e2 - nu
            f = -np.sum(w * ll) + self.reg * (np.sum((att - pa) ** 2) + np.sum((dfn - pd_) ** 2))

            # analitik gradyan
            g1 = x - lam
            g2 = y - nu
            gr = np.zeros_like(lam)
            g1[m00] += -lam[m00] * nu[m00] * rho / tau[m00]
            g2[m00] += -lam[m00] * nu[m00] * rho / tau[m00]
            gr[m00] = -lam[m00] * nu[m00] / tau[m00]
            g1[m01] += lam[m01] * rho / tau[m01]
            gr[m01] = lam[m01] / tau[m01]
            g2[m10] += nu[m10] * rho / tau[m10]
            gr[m10] = nu[m10] / tau[m10]
            gr[m11] = -1 / tau[m11]
            g1 *= w; g2 *= w; gr *= w
            grad = np.zeros_like(p)
            grad[0] = -(g1.sum() + g2.sum())
            grad[1] = -g1.sum()
            grad[2] = -gr.sum()
            ga = np.bincount(h, g1, n) + np.bincount(a, g2, n)
            gd = np.bincount(a, g1, n) + np.bincount(h, g2, n)
            grad[3:3 + n] = -ga + 2 * self.reg * (att - pa)
            grad[3 + n:] = -gd + 2 * self.reg * (dfn - pd_)
            return f, grad

        p0 = np.zeros(3 + 2 * n)
        p0[0] = np.log(max((x * w).sum() + (y * w).sum(), 1) / (2 * w.sum()))
        p0[1] = 0.2
        bounds = [(None, None), (None, None), (-0.3, 0.3)] + [(None, None)] * (2 * n)
        res = minimize(nll, p0, jac=True, method="L-BFGS-B", bounds=bounds)
        p = res.x
        self.mu, self.home, self.rho = p[0], p[1], p[2]
        self.att = dict(zip(self.teams, p[3:3 + n]))
        self.dfn = dict(zip(self.teams, p[3 + n:]))
        return self

    def expected_goals(self, home, away):
        a_h, d_h = self.att.get(home, 0.0), self.dfn.get(home, 0.0)
        a_a, d_a = self.att.get(away, 0.0), self.dfn.get(away, 0.0)
        lam = np.exp(self.mu + self.home + a_h + d_a)
        nu = np.exp(self.mu + a_a + d_h)
        return lam, nu

    def score_matrix(self, home, away):
        lam, nu = self.expected_goals(home, away)
        g = np.arange(MAX_GOALS + 1)
        M = np.outer(poisson.pmf(g, lam), poisson.pmf(g, nu))
        r = self.rho
        M[0, 0] *= 1 - lam * nu * r
        M[0, 1] *= 1 + lam * r
        M[1, 0] *= 1 + nu * r
        M[1, 1] *= 1 - r
        return M / M.sum()

    def probs_1x2(self, home, away):
        M = self.score_matrix(home, away)
        return np.tril(M, -1).sum(), np.trace(M), np.triu(M, 1).sum()
