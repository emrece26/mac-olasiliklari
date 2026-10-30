"""Geriye dönük test: modeli yalnızca maçtan ÖNCEKİ verilerle kurup
1/X/2 tahminlerini gerçek sonuçlarla karşılaştırır (her 14 günde bir yeniden eğitim)."""
import itertools
import json
import sys
from datetime import timedelta

import numpy as np
import pandas as pd

from model import DixonColes

LEAGUES = ["SUPERLIG", "EPL", "LALIGA", "SERIEA", "BUNDESLIGA", "LIGUE1"]


def test_season(df, league):
    """Test sezonu: verideki son tamamlanmış sezon (içinde bulunulandan bir önceki)."""
    seasons = sorted(df[df.league == league].season.unique())
    return seasons[-2] if len(seasons) > 1 else seasons[-1]
WINDOW_DAYS = 3 * 365


def load(path="matches.csv"):
    df = pd.read_csv(path, parse_dates=["date"])
    return df


PROMOTED = 0.0  # yükselen takım önseli (komut satırından ayarlanır)


def promoted_prior(tr, cut, strength):
    """Eğitim penceresinin ilk sezonunda olmayan takımlara (sonradan yükselenler) zayıf önsel."""
    if strength == 0:
        return {}
    first_season = tr.season.min()
    old = set(tr[tr.season == first_season].home) | set(tr[tr.season == first_season].away)
    teams = set(tr.home) | set(tr.away)
    return {t: (-strength, strength) for t in teams - old}


def run(df, league, xi, reg, step=14, promoted=0.0):
    d = df[(df.league == league) & df.hg.notna()].copy()
    test = d[d.season == test_season(df, league)].sort_values("date")
    start, end = test.date.min(), test.date.max()
    out = []
    cut = start
    while cut <= end:
        nxt = cut + timedelta(days=step)
        tr = d[(d.date < cut) & (d.date >= cut - timedelta(days=WINDOW_DAYS))]
        prior = promoted_prior(tr, cut, promoted)
        # test edilecek ama eğitimde hiç olmayan takımlar da yükselen sayılır
        for t in set(test.home) | set(test.away):
            if t not in set(tr.home) | set(tr.away) and promoted:
                prior[t] = (-promoted, promoted)
        teams = sorted(set(tr.home) | set(tr.away) | set(test.home) | set(test.away))
        m = DixonColes(xi, reg).fit(tr.home, tr.away, tr.hg, tr.ag, (cut - tr.date).dt.days, teams=teams, prior=prior)
        base = np.array([(tr.hg > tr.ag).mean(), (tr.hg == tr.ag).mean(), (tr.hg < tr.ag).mean()])
        for r in test[(test.date >= cut) & (test.date < nxt)].itertuples():
            p = np.array(m.probs_1x2(r.home, r.away))
            res = 0 if r.hg > r.ag else (1 if r.hg == r.ag else 2)
            out.append((p, base, res))
        cut = nxt
    P = np.array([o[0] for o in out]); B = np.array([o[1] for o in out])
    R = np.array([o[2] for o in out]); Y = np.eye(3)[R]

    def ll(Q): return -np.mean(np.log(Q[np.arange(len(R)), R]))
    def rps(Q): return np.mean(np.sum((np.cumsum(Q, 1) - np.cumsum(Y, 1))[:, :2] ** 2, 1) / 2)
    return {"n": len(R), "logloss": ll(P), "logloss_base": ll(B), "rps": rps(P), "rps_base": rps(B),
            "acc": float(np.mean(P.argmax(1) == R)), "acc_base": float(np.mean(B.argmax(1) == R))}


if __name__ == "__main__":
    df = load()
    leagues = sys.argv[1:] or LEAGUES
    grid = list(itertools.product([0.001, 0.002, 0.004], [0.5, 2.0, 5.0]))
    import os
    best = json.load(open("backtest_results.json")) if os.path.exists("backtest_results.json") else {}
    for lg in leagues:
        rows = []
        for xi, reg in grid:
            r = run(df, lg, xi, reg)
            rows.append((r["logloss"], xi, reg, r))
            if False: print(f"{lg:10s} xi={xi} reg={reg}: logloss={r['logloss']:.4f} rps={r['rps']:.4f} acc={r['acc']:.3f}", flush=True)
        rows.sort(key=lambda t: t[0])
        _, xi, reg, r = rows[0]
        best[lg] = {"xi": xi, "reg": reg, "season": test_season(df, lg), **{k: round(float(v), 4) for k, v in r.items()}}
        print("BEST", lg, best[lg], flush=True)
    json.dump(best, open("backtest_results.json", "w"), indent=2)
