"""football-data.co.uk'den sonuç ve fikstür dosyalarını indirir.

İndirilenler data/ klasörüne yazılır:
  data/results/{LIG}_{SEZON}.csv   ör. T1_2627.csv (2026-27 Süper Lig)
  data/fixtures.csv                 önümüzdeki maçlar (tüm ligler)

Bir dosya indirilemezse eski kopyası korunur; böylece site hiçbir zaman boş kalmaz.
"""
import os
import sys
import time
from datetime import date

import requests

DIVS = ["T1", "E0", "SP1", "I1", "D1", "F1"]
SEASONS_BACK = 4  # içinde bulunulan sezon + önceki 4 sezon
BASE = "https://www.football-data.co.uk"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HEADERS = {"User-Agent": "Mozilla/5.0 (mac-olasiliklari; haftalik guncelleme)"}


def season_codes(today=None):
    today = today or date.today()
    y0 = today.year if today.month >= 7 else today.year - 1
    return [f"{(y % 100):02d}{((y + 1) % 100):02d}" for y in range(y0 - SEASONS_BACK, y0 + 1)]


def fetch(url, path):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200 and b"," in r.content[:200]:
                tmp = path + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(r.content)
                os.replace(tmp, path)
                return True
            print(f"  {url}: HTTP {r.status_code}")
            if r.status_code == 404:
                return False
        except requests.RequestException as e:
            print(f"  {url}: {e}")
        time.sleep(3 * (attempt + 1))
    return False


def main():
    os.makedirs(os.path.join(OUT, "results"), exist_ok=True)
    ok = fail = 0
    codes = season_codes()
    for s in codes:
        for d in DIVS:
            path = os.path.join(OUT, "results", f"{d}_{s}.csv")
            # Eski sezonlar değişmez; zaten varsa tekrar indirme
            if s != codes[-1] and os.path.exists(path):
                continue
            if fetch(f"{BASE}/mmz4281/{s}/{d}.csv", path):
                ok += 1
                print(f"indirildi: {d} {s}")
            else:
                fail += 1
    if fetch(f"{BASE}/fixtures.csv", os.path.join(OUT, "fixtures.csv")):
        print("indirildi: fikstür")
    else:
        fail += 1
    print(f"tamam: {ok} dosya indirildi, {fail} başarısız")
    # Güncel sezonun hiçbir dosyası yoksa iş akışı hata versin ki fark edilsin
    have_current = any(os.path.exists(os.path.join(OUT, "results", f"{d}_{codes[-1]}.csv")) for d in DIVS)
    if not have_current:
        sys.exit("Güncel sezon verisi indirilemedi.")


if __name__ == "__main__":
    main()
