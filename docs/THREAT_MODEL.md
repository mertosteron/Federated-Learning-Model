# FedGuard — Tehdit Modeli (STRIDE)

**Sürüm:** 0.1 (Faz 0)
**Son güncelleme:** 2026-04-23
**Durum:** Taslak. Her PR'da güncellenir (CLAUDE.md Katı Kural #4).

---

## 1. Kapsam

Bu doküman FedGuard federe AML tespit ağının güvenlik tehditlerini STRIDE
(Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service,
Elevation of Privilege) çerçevesiyle modeller. Her aktör için varsayılan güven
düzeyi, saldırı vektörleri ve mimari kontroller listelenir.

Kapsam dışı: banka çekirdek bankacılık sistemlerinin kendi güvenliği
(L0 katmanı — bankaların sorumluluğu), son kullanıcı cihaz güvenliği,
düzenleyici organın kendi altyapısı.

---

## 2. Varlıklar (Assets)

| ID | Varlık | Hassasiyet | Konum |
|----|--------|------------|-------|
| A1 | Ham işlem kayıtları | Kritik (PII + finansal) | Yalnızca L0/L1, banka VPC'si içinde |
| A2 | Yerel model ağırlıkları (Δw) | Yüksek (bilgi sızdırır) | L1'de üretilir, maskelenerek L2'ye gider |
| A3 | Global model ağırlıkları | Orta (halka açık değil) | IPFS + on-chain CID |
| A4 | Müşteri embedding'leri | Yüksek (membership inference riski) | L1'de tutulur, asla dışarı çıkmaz |
| A5 | Dolandırıcı centroid'leri | Düşük (anonimleştirilmiş) | IPFS + zincir üstü |
| A6 | ZK ispatları | Sıfır (tanım gereği sıfır bilgi) | Zincir üstü |
| A7 | Banka gizli anahtarları | Kritik | HSM / secure enclave |
| A8 | Audit logları | Yüksek (değiştirilemez olmalı) | Zincir üstü append-only |
| A9 | `AlertRaised` event'leri | Orta (314(b) opt-in ile açıklanabilir) | Zincir üstü |

---

## 3. Aktörler ve Güven Varsayımları

### 3.1 Kötü niyetli banka (Malicious Participant)
**Güven düzeyi:** Byzantine — kasten zarar verebilir.
**Yetenekler:** Kendi yerel verisine tam erişim; kendi gradyanını seçme; kötü
ispat üretmeye çalışma; protokol mesajlarını sahteleme; başka bir bankanın
kimliğine bürünmeye çalışma.
**Motivasyon:** Model zehirleme (kendi müşterilerinin dolandırıcı olarak
etiketlenmemesi), rekabet verisi çalma, sistemi devre dışı bırakma.

### 3.2 Yarı-dürüst toplayıcı (Honest-but-curious Aggregator)
**Güven düzeyi:** Protokolü takip eder ama gözlemlediği her şeyi sızdırmaya
çalışır. Toplama komitesinin ≤1 üyesi tam Byzantine olabilir (n=3, t=1).
**Yetenekler:** Maskelenmiş gradyanları, ispat meta-verisini, zamanlama
sinyallerini görür. Gradyan içeriğini açamaz (SecAgg garantisi).
**Motivasyon:** Banka müşteri popülasyonu hakkında istatistik çıkarmak,
membership inference.

### 3.3 Dışarıdan saldırgan (External Adversary)
**Güven düzeyi:** Sıfır — kötücül.
**Yetenekler:** Ağ trafiğini dinleme (MITM), sahte sertifika sunma, DDoS,
zincir üstü event'leri okuma, kamuya açık IPFS içeriğini çekme.
**Motivasyon:** Müşteri verisi çalma, sistem durdurma, fidye.

### 3.4 Uyumluluk denetçisi (Compliance Auditor)
**Güven düzeyi:** Meşru — yasal yetki ile gelir.
**Yetenekler:** Zincir üstü tüm kayıtlara read-only erişim; model yeniden
oynatma; SAR tetikleyicilerini inceleme. **Ham PII'ye erişemez** (bankalar
her zaman kendi kayıtları üzerinde sorumlu).
**Motivasyon:** BSA §5318 uyumunu doğrulamak.

---

## 4. STRIDE Matrisi

### S — Spoofing (Kimlik sahteleme)

| Tehdit | Aktör | Varlık | Kontrol | Katman |
|--------|-------|--------|---------|--------|
| Başka bir banka gibi katkı gönderme | 3.1 / 3.3 | A2 | Banka başına X.509 sertifikası + `HMAC(bank_secret, round_id)` ZK public signal olarak | L2 + Faz 4 devresi |
| Sahte toplayıcı komitesi kurma | 3.3 | A2 | Permissioned Besu ağı; toplayıcı set'i smart contract'ta whitelist | L3 |
| Müşteri kimliği sahteciliği (KYC bypass) | 3.1 | A1 | Kapsam dışı — L0 bankaya ait | L0 |

### T — Tampering (Veri/model bozma)

| Tehdit | Aktör | Varlık | Kontrol | Katman |
|--------|-------|--------|---------|--------|
| Gradyan zehirleme (scale-up saldırısı) | 3.1 | A2 / A3 | Groth16 ile `‖Δw‖₂ ≤ clip_norm` ispatı (Faz 4) + Krum / Coordinate-wise Median (Faz 3) | L2 |
| Sybil gradyan enjeksiyonu | 3.1 | A3 | Whitelist + nullifier (tek tur bir katılım) | L3 Faz 4 |
| Tur sırasında global modeli tahrif | 3.2 | A3 | IPFS content-addressed hash, on-chain CID tanığı | L3 |
| Audit log silme/değiştirme | 3.1 / 3.2 | A8 | Besu append-only event log; finality IBFT 2.0 ile garanti | L3 |

### R — Repudiation (İnkar)

| Tehdit | Aktör | Varlık | Kontrol | Katman |
|--------|-------|--------|---------|--------|
| Banka "ben katkı vermedim" diyor | 3.1 | A8 | Her `ContributionAccepted` event'i `bankId + roundId + nullifier` imzalı | L3 Faz 4 |
| Toplayıcı "global model bu değildi" diyor | 3.2 | A3 | Zincir üstü CID + hash tanığı; IPFS yeniden üretilebilir | L3 Faz 6 |
| Denetçi sorgusuna "kayıt yok" yanıtı | 3.1 | A8 | `audit_replay.py` deterministik olarak yeniden oynatır | L4 Faz 6 |

### I — Information Disclosure (Bilgi sızdırma)

| Tehdit | Aktör | Varlık | Kontrol | Katman |
|--------|-------|--------|---------|--------|
| Gradyandan örneklem tersine mühendisliği | 3.2 | A1 / A4 | Opacus DP-SGD (ε=3, δ=1e-6) + per-sample clipping (Faz 2) | L1 |
| Maskelenmemiş gradyan toplayıcıda görülür | 3.2 | A2 | SecAgg+ pairwise masking; ≥2 komite üyesi dürüst olduğu sürece açılmaz | L2 |
| Embedding'den müşteri kimliği çıkarımı | 3.2 / 3.3 | A4 | Embedding'ler L1'de kalır; yalnızca centroid'ler yayınlanır | L1 |
| Ağ trafiği dinleme | 3.3 | A2 | gRPC + TLS 1.3, karşılıklı (mTLS) kimlik doğrulama | L2 |
| Zincir üstü event'ten banka müşteri sayısı tahmini | 3.3 | A9 | Batching + dummy event'lerle zamanlama maskesi (Faz 5 NB) | L3 |
| Membership inference saldırısı | 3.2 / 3.3 | A4 | Hedef: saldırı AUC ≤ 0.55 (Faz 2 kabul kriteri) | L1 |

### D — Denial of Service

| Tehdit | Aktör | Varlık | Kontrol | Katman |
|--------|-------|--------|---------|--------|
| Bir toplayıcı düşer | 3.3 | Sistem | IBFT 2.0 ile t≤1 hata tolere eder (n=3) | L2 |
| Banka katılmaz | — | Sistem | Flower cohort seçimi minimum katılım oranı (örn. 3/5) ile tur başlatır | L2 |
| Zincir spam | 3.3 | A8 | Permissioned Besu; yazma hakkı whitelist'e bağlı | L3 |
| ZK prover bomba (tanımsız süreli ispat) | 3.1 | Sistem | Devre sabit kısıtlı; timeout ≤ 30 sn | L1 Faz 4 |

### E — Elevation of Privilege

| Tehdit | Aktör | Varlık | Kontrol | Katman |
|--------|-------|--------|---------|--------|
| Toplayıcı → banka veri erişimi | 3.2 | A1 | Mimari tek-yönlü: veri asla L1 dışına çıkmaz | L1/L2 sınırı |
| Denetçi → ham PII erişimi | 3.4 | A1 | Sadece on-chain read-only; PII zincire hiç yazılmaz | L3 / L4 |
| Kullanıcı / operatör → gizli anahtar | 3.3 | A7 | HSM + `.env` repoda yasak (güvenlik check-list Faz 7) | L1 |

---

## 5. Güven Varsayımları Özeti

- **En az 2/3 toplayıcı dürüst.** SecAgg açılması için bu gerekir.
- **En az 4/5 banka dürüst.** DWFL doğruluk-ağırlıklı toplama ve Krum savunması
  1 Byzantine bankayı kaldırabilir.
- **Powers of Tau phase-1 güvenilir.** MVP'de phase-2 contribution tek taraflı;
  üretimde çok-taraflı MPC seremonisi zorunludur (COMPLIANCE.md'de işaretli).
- **TLS PKI'si işler durumda.** Saldırgan sertifika otoritesine erişemez.
- **Besu validator set'i en az 2/3 dürüst.** IBFT 2.0 gerekliliği (n=4 için
  f≤1).

---

## 6. Açık Tehditler / Kabul Edilen Riskler

- **Yan-kanal zamanlama saldırıları**: Bir bankanın ispat üretim süresi müşteri
  yoğunluğu hakkında sinyal verebilir. MVP kapsamında ele alınmadı; Faz 7'de
  sabit-süreli prover sarmalayıcı değerlendirilecek.
- **Eğitim öncesi veri poisoning**: Bir banka kendi eğitim verisine sentetik
  "iyi görünen" kayıtlar ekleyebilir. Yalnızca davranışsal anomali tespiti
  (DWFL ağırlık düşüşü) ile kısmen azaltılır.
- **Trusted setup (Faz 4) tek taraflı**: MVP sınırı; üretim için MPC seremonisi
  zorunlu kılınır.

---

## 7. Güncelleme Disiplini

Her PR, değişiklikle ortaya çıkan yeni tehditleri bu belgeye eklemeli
veya kaldırılan kontrolleri işaretlemelidir. Yapılmazsa PR bloke edilir
(CLAUDE.md Katı Kural #4).
