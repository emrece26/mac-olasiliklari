# Maç Olasılıkları

Süper Lig, Premier Lig, La Liga, Serie A, Bundesliga ve Ligue 1 maçları için olasılık tahmini yapan site.
Haftada iki kez (salı ve cuma sabahı) **kendiliğinden** güncellenir:

1. `update_data.py` football-data.co.uk'den son 5 sezonun sonuçlarını ve sıradaki maçları indirir.
2. `prepare_data.py` dosyaları tek tabloya çevirir.
3. `backtest.py` her ayın ilk çalıştırmasında model ayarlarını geçen sezona göre yeniden seçer.
4. `build_site.py` modeli kurar ve `site/index.html` dosyasını üretir.
5. Site GitHub Pages'te yayınlanır.

## Kurulum (bir kez, ~5 dakika)

1. **Depo oluşturun.** github.com'da sağ üstteki **+** → **New repository**.
   Ad: `mac-olasiliklari`. **Public** seçin (ücretsiz GitHub Pages için gerekli). **Create repository**.
2. **Dosyaları yükleyin.** Yeni depoda **uploading an existing file** bağlantısına tıklayın.
   Zip'ten çıkardığınız klasörün **içindeki her şeyi** (gizli `.github` klasörü dahil) sürükleyip bırakın, **Commit changes**.
   > Mac'te `.github` klasörü gizlidir: Finder'da `Cmd + Shift + .` ile görünür yapın.
3. **Pages'i açın.** Depoda **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. **Yazma izni verin.** **Settings → Actions → General → Workflow permissions → Read and write permissions → Save**.
5. **İlk çalıştırma.** **Actions** sekmesi → soldan **Haftalık güncelleme** → **Run workflow**.
   2-3 dakika sonra yeşil tik çıkar. Site adresi: `https://KULLANICIADINIZ.github.io/mac-olasiliklari/`

Bundan sonra hiçbir şey yapmanız gerekmez.

## Sorun olursa

- **Actions'ta kırmızı çarpı:** üzerine tıklayıp hangi adımın kırmızı olduğuna bakın.
  "Veriyi indir" adımıysa football-data.co.uk geçici olarak erişilemiyor olabilir; bir sonraki çalıştırma düzeltir.
- **GitHub, 60 gün boyunca depoda hiçbir değişiklik olmazsa zamanlanmış görevleri durdurur.** Bu iş akışı her çalıştığında veriyi depoya kaydettiği için normalde durmaz. Durursa Actions sekmesinde **Enable workflow** düğmesine basmanız yeterli.

## Kendi bilgisayarınızda çalıştırmak

```bash
pip install -r requirements.txt
python update_data.py && python prepare_data.py && python build_site.py
# site/index.html dosyasını tarayıcıda açın
```

## Dosyalar

| Dosya | Görev |
|---|---|
| `model.py` | Zaman ağırlıklı Dixon-Coles modeli |
| `backtest.py` | Geriye dönük test, en iyi ayarları `backtest_results.json`'a yazar |
| `template.html` | Sitenin tasarımı; `build_site.py` veriyi içine yerleştirir |
| `.github/workflows/guncelle.yml` | Zamanlama: salı ve cuma 06:17 (TR). Değiştirmek için `cron` satırlarını düzenleyin (saatler UTC) |
