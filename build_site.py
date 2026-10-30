"""Her lig için son modeli kurar ve siteyi (site/index.html) üretir."""
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from model import DixonColes

HERE = os.path.dirname(os.path.abspath(__file__))
LEAGUES = {
    "SUPERLIG": "Süper Lig", "EPL": "Premier Lig", "LALIGA": "La Liga",
    "SERIEA": "Serie A", "BUNDESLIGA": "Bundesliga", "LIGUE1": "Ligue 1",
}
WINDOW_DAYS = 3 * 365
PROMOTED = 0.15        # geçmiş verisi olmayan (yükselen) takımlar için zayıf başlangıç varsayımı
DEFAULT = {"xi": 0.0015, "reg": 2.0}


def standings(cur):
    t = {}
    for r in cur.itertuples():
        for team, gf, ga in ((r.home, r.hg, r.ag), (r.away, r.ag, r.hg)):
            s = t.setdefault(team, [0, 0, 0, 0, 0, 0])  # O G B M AG YG
            s[0] += 1; s[4] += gf; s[5] += ga
            s[1 if gf > ga else (2 if gf == ga else 3)] += 1
    return t


def main():
    df = pd.read_csv(os.path.join(HERE, "matches.csv"), parse_dates=["date"])
    up = pd.read_csv(os.path.join(HERE, "upcoming.csv"))
    btp = os.path.join(HERE, "backtest_results.json")
    bt = json.load(open(btp)) if os.path.exists(btp) else {}
    now = datetime.now(ZoneInfo("Europe/Istanbul"))
    out = {}
    for lg, label in LEAGUES.items():
        played = df[df.league == lg]
        if played.empty:
            print(lg, "veri yok, atlandı")
            continue
        ref = played.date.max()
        tr = played[played.date >= ref - timedelta(days=WINDOW_DAYS)]
        season = sorted(played.season.unique())[-1]
        cur = played[played.season == season]
        fx = up[up.league == lg]

        # Bu sezonun takımları: oynananlar + fikstürdekiler (sezon başında yalnızca fikstür olabilir)
        cur_teams = set(cur.home) | set(cur.away) | set(fx.home) | set(fx.away)
        seasons = sorted(played.season.unique())
        if len(cur_teams) < 10 and len(seasons) > 1:  # sezon başı, fikstür henüz yok
            last = played[played.season == seasons[-2]]
            cur_teams |= set(last.home) | set(last.away)
        older = tr[tr.season != season]
        known = set(older.home) | set(older.away)
        prior = {t: (-PROMOTED, PROMOTED) for t in cur_teams if t not in known}

        p = bt.get(lg, DEFAULT)
        teams_all = sorted(set(tr.home) | set(tr.away) | cur_teams)
        m = DixonColes(p["xi"], p["reg"]).fit(tr.home, tr.away, tr.hg.astype(int), tr.ag.astype(int),
                                             (ref - tr.date).dt.days, teams=teams_all, prior=prior)
        st = standings(cur)
        teams = {t: {"a": round(m.att[t], 4), "d": round(m.dfn[t], 4), "st": [int(v) for v in st.get(t, [0] * 6)],
                     "new": t in prior} for t in sorted(cur_teams)}
        fixtures = [[r.date, r.home, r.away, r.time if isinstance(r.time, str) else "", False]
                    for r in fx.itertuples() if r.home in teams and r.away in teams][:18]
        out[lg] = {
            "name": label, "ref": ref.strftime("%Y-%m-%d"), "mu": round(m.mu, 4), "home": round(m.home, 4),
            "rho": round(m.rho, 4), "teams": teams, "fixtures": fixtures,
            "nTrain": int(len(tr)), "updated": now.strftime("%Y-%m-%d %H:%M"),
            "bt": {k: bt[lg][k] for k in ("n", "logloss", "logloss_base", "rps", "rps_base", "acc", "acc_base")} if lg in bt else None,
            "btSeason": bt.get(lg, {}).get("season", ""),
        }
        print(f"{lg}: son maç {ref.date()}, {len(tr)} maçla eğitildi, {len(fixtures)} sıradaki maç")

    html = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    html = html.replace("__DATA__", json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    os.makedirs(os.path.join(HERE, "site"), exist_ok=True)
    open(os.path.join(HERE, "site", "index.html"), "w", encoding="utf-8").write(html)


if __name__ == "__main__":
    main()
