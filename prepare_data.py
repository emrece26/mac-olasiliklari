"""data/ klasöründeki football-data.co.uk dosyalarını iki tabloya çevirir:
  matches.csv   oynanmış maçlar (lig, sezon, tarih, ev, deplasman, gol, gol)
  upcoming.csv  sıradaki maçlar (lig, tarih, Türkiye saati, ev, deplasman)
"""
import csv
import glob
import io
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DIV_TO_LEAGUE = {"T1": "SUPERLIG", "E0": "EPL", "SP1": "LALIGA", "I1": "SERIEA", "D1": "BUNDESLIGA", "F1": "LIGUE1"}

# football-data.co.uk'deki Türk takım adları → sitede gösterilecek ad
TR_NAMES = {
    "Besiktas": "Beşiktaş", "Buyuksehyr": "Başakşehir", "Corum": "Çorum FK", "Fenerbahce": "Fenerbahçe",
    "Genclerbirligi": "Gençlerbirliği", "Goztep": "Göztepe", "Rizespor": "Çaykur Rizespor",
    "Karagumruk": "Fatih Karagümrük", "Ad. Demirspor": "Adana Demirspor", "Ankaragucu": "Ankaragücü",
    "Istanbulspor": "İstanbulspor", "Kasimpasa": "Kasımpaşa", "Eyupspor": "Eyüpspor", "Gaziantep": "Gaziantep FK",
    "Bodrumspor": "Bodrumspor", "Amedspor": "Amedspor", "Erzurumspor": "Erzurumspor",
}


def name(div, n):
    n = n.strip()
    return TR_NAMES.get(n, n) if div == "T1" else n


def read_csv(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    return [r for r in csv.DictReader(io.StringIO(text)) if r.get("Div") and r.get("HomeTeam")]


def parse_date(s):
    d, m, y = s.strip().split("/")
    y = int(y)
    return date(y + 2000 if y < 100 else y, int(m), int(d))


def season_of(d):
    y0 = d.year if d.month >= 7 else d.year - 1
    return f"{y0}-{str(y0 + 1)[2:]}"


def uk_to_tr(d, t):
    """football-data saatleri İngiltere saatidir; Türkiye saatine çevir."""
    if not t:
        return d, ""
    hh, mm = map(int, t.strip().split(":")[:2])
    uk = datetime(d.year, d.month, d.day, hh, mm, tzinfo=ZoneInfo("Europe/London"))
    tr = uk.astimezone(ZoneInfo("Europe/Istanbul"))
    return tr.date(), tr.strftime("%H:%M")


def main():
    played = {}
    for path in sorted(glob.glob(os.path.join(DATA, "results", "*.csv"))):
        for r in read_csv(path):
            lg = DIV_TO_LEAGUE.get(r["Div"].strip())
            if not lg or not r.get("FTHG") or not r.get("FTAG"):
                continue
            d = parse_date(r["Date"])
            h, a = name(r["Div"], r["HomeTeam"]), name(r["Div"], r["AwayTeam"])
            played[(lg, d.isoformat(), h, a)] = [lg, season_of(d), d.isoformat(), h, a, int(float(r["FTHG"])), int(float(r["FTAG"]))]
    rows = sorted(played.values(), key=lambda x: (x[0], x[2]))
    with open(os.path.join(HERE, "matches.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["league", "season", "date", "home", "away", "hg", "ag"])
        w.writerows(rows)

    up = []
    fx = os.path.join(DATA, "fixtures.csv")
    if os.path.exists(fx):
        done = {(x[0], x[3], x[4], x[1]) for x in rows}
        for r in read_csv(fx):
            lg = DIV_TO_LEAGUE.get(r["Div"].strip())
            if not lg:
                continue
            d, t = uk_to_tr(parse_date(r["Date"]), r.get("Time", ""))
            h, a = name(r["Div"], r["HomeTeam"]), name(r["Div"], r["AwayTeam"])
            if (lg, h, a, season_of(d)) in done:
                continue
            up.append([lg, d.isoformat(), t, h, a])
    up.sort(key=lambda x: (x[0], x[1], x[2]))
    with open(os.path.join(HERE, "upcoming.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["league", "date", "time", "home", "away"])
        w.writerows(up)

    from collections import Counter
    c = Counter((r[0], r[1]) for r in rows)
    for k in sorted(c):
        print(*k, c[k], "maç")
    print("sıradaki maç:", len(up))


if __name__ == "__main__":
    main()
