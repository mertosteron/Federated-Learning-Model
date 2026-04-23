# FedGuard

**Bankalar arası, gizlilik korumalı, federe AML ve dolandırıcılık tespit ağı.**

5 bankanın ham müşteri verisini hiçbir koşulda birbiriyle paylaşmadan,
kurumlar arası dolandırıcı halkalarını (layering ring, smurfing cluster,
sentetik kimlik halkası) tespit edebilmesini sağlar.

> Bu bir **prototiptir**. Üretime geçmeden önce bağımsız kriptografi
> denetimi, red-team testi ve yerel düzenleyici (BDDK / FinCEN / FCA)
> görüşmesi zorunludur.

---

## Teknik temel

| Katman | Teknoloji |
|--------|-----------|
| Federe öğrenme | Flower ≥ 1.8 + DWFL ağırlıklı FedAvg |
| Model | GraphSAGE (PyTorch Geometric 2.5) |
| Gizlilik | Opacus DP-SGD (ε=3, δ=1e-6) + SecAgg+ |
| Sıfır bilgi | Circom 2.1 + Groth16 (snarkjs) |
| Blokzinciri | Hyperledger Besu 24.x, IBFT 2.0 |
| Depolama | IPFS (ağırlıklar) + zincir üstü hash |
| Mesajlaşma | gRPC + TLS 1.3 |

Tam teknik gerekçe: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
Tehdit modeli: [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md)
Uyum haritası: [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md)

---

## Hızlı başlangıç

```bash
git clone <repo>
cd FL_Project

# Ortamı ayağa kaldır (Faz 0 placeholder servisler)
make up

# docker-compose sentaks doğrulaması
make validate

# Testler
make test

# Uçtan uca demo (Faz 7 sonrası)
make demo

# Temizlik
make clean
```

---

## Fazlar ve durum

| Faz | Başlık | Durum |
|-----|--------|-------|
| 0 | Repo iskeleti + tehdit modeli | **Tamamlandı** |
| 1 | Sentetik veri + graf inşası | Planlanan |
| 2 | Yerel GNN + DP-SGD | Planlanan |
| 3 | SecAgg ile federe eğitim | Planlanan |
| 4 | ZK-SNARK katkı ispatı | Planlanan |
| 5 | Kurumlar arası ZK uyarı | Planlanan |
| 6 | Blokzinciri audit izi | Planlanan |
| 7 | Demo + dağıtım | Planlanan |

Her fazın kabul raporu: `docs/phase-reports/PHASE_N.md`

---

## Dizin yapısı

```
FL_Project/                    (fedguard monorepo kökü)
├── bank-node/        # Her bankanın kendi VPC'sinde çalıştıracağı düğüm
├── aggregator/       # Toplama komitesi (n=3, BFT)
├── circuits/         # Circom ZK devreleri
├── contracts/        # Solidity sözleşmeleri
├── common/           # Proto şemaları
├── simulation/       # 5 banka sentetik veri + değerlendirme
├── dashboard/        # Opsiyonel operatör UI (TS)
├── docs/             # Mimari, tehdit modeli, uyum
├── tests/            # Python test suite
└── docker-compose.yml
```

---

## Katı kurallar (CLAUDE.md §0)

1. Sahte (mock) kripto kullanılmaz — her ZK devresi gerçek Groth16.
2. Ham işlem verisi dışarı çıkaran API / log açılmaz.
3. Audit izleri zincir üstünde deterministik yeniden üretilebilir.
4. Her PR'da `THREAT_MODEL.md` güncellenir.
5. Belirsizlikte varsayım yazılır, sessiz karar alınmaz.

---

## Güvenlik

Açık güvenlik bulguları için: bkz. `docs/THREAT_MODEL.md` §6.
Responsible disclosure: repo maintainer'a özel iletişim.

## Lisans

TBD — kurumsal katılımcı anlaşması gerektirir.
