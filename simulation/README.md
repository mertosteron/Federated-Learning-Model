# simulation

5 bankalı sentetik evren üreteci. Gerçek müşteri verisi **asla** kullanılmaz.

- `data_generator.py` — Faz 1: her banka için 10k dürüst müşteri + 100 dolandırıcı profili
- 3 dolandırıcılık tipi: layering ring, smurfing cluster, synthetic identity ring
- `ground_truth.parquet` — yalnızca değerlendirme için tutulur; model görmez
- `evaluate_local.py` — Faz 1: izole banka baseline (federasyonun değerini göstermek için)
