# FedGuard — Sistem Mimarisi

**Sürüm:** 0.1 (Faz 0)
**Son güncelleme:** 2026-04-23

---

## 1. Katmanlar (L0–L4)

```
┌────────────────────────────────────────────────────────────────┐
│  L4: Düzenleyici Denetim Katmanı                               │
│      - audit_replay.py (Python)                                │
│      - Besu RPC read-only erişim + IPFS gateway                │
├────────────────────────────────────────────────────────────────┤
│  L3: Blokzinciri Sabitleme Katmanı                             │
│      - Hyperledger Besu 24.x, IBFT 2.0, 4 validator            │
│      - Solidity 0.8.24 sözleşmeleri                            │
│        * FedGuardRegistry (ispat kabul + nullifier)            │
│        * RoundOrchestrator (tur yaşam döngüsü)                 │
│        * AuditLog (append-only uyarı kaydı)                    │
│        * AlertVerifier (mesafe ispatı)                         │
│      - IPFS (model ağırlıkları, zincir-dışı)                   │
├────────────────────────────────────────────────────────────────┤
│  L2: Koordinasyon & Toplama Katmanı                            │
│      - Flower sunucusu (Python) + SecAgg+                      │
│      - DWFL ağırlıklandırma stratejisi                         │
│      - Groth16 doğrulayıcı (zincir üstüne delege)              │
│      - Krum / Coord-wise Median poisoning savunması            │
│      - 3-düğümlü BFT toplayıcı komitesi                        │
├────────────────────────────────────────────────────────────────┤
│  L1: Banka Düğümü (banka VPC'si)                               │
│      - PyTorch 2.3 + PyG 2.5 GraphSAGE                         │
│      - Opacus 1.5 DP-SGD (ε=3, δ=1e-6)                         │
│      - Flower NumPyClient                                      │
│      - snarkjs Groth16 prover                                  │
│      - Yerel işlem grafiği (heterojen)                         │
├────────────────────────────────────────────────────────────────┤
│  L0: Banka Çekirdek Bankacılık (bankaya ait, read-only ETL)    │
│      - Dışa VERİ ÇIKMAZ — yalnızca L1 için besleyici           │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. Veri Akışı

### 2.1 Eğitim Turu (Faz 3 akışı, genişletilmiş)

1. **Tur başlatma** (L2 → L3): `RoundOrchestrator.startRound(roundId, modelCID)`
2. **Global model indirme** (L3 → L1): Her banka IPFS'den `modelCID`'i çeker.
3. **Yerel DP-SGD** (L1): Opacus ile per-sample clipping + Gaussian noise.
4. **Gradyan kırpma** (L1): `‖Δw_i‖₂ ≤ clip_norm`.
5. **Pedersen commitment** (L1): `C_i = PedersenCommit(Δw_i, r_i)`.
6. **ZK ispat üretimi** (L1): Groth16, `contribution.circom` devresi.
7. **SecAgg maskeleme** (L1): Pairwise maske `m_ij`, Shamir fallback (Faz 3).
8. **Gönderim** (L1 → L2): `(maskedΔw_i, commitment, proof)` gRPC/TLS üzerinden.
9. **Zincir üstü doğrulama** (L2 → L3): `FedGuardRegistry.submitProof(...)`
   Groth16 verifikasyonu, nullifier kontrolü, `ContributionAccepted` event.
10. **Toplama** (L2): DWFL + Krum; SecAgg maskelerini iptal ederek yalnızca
    toplamı elde eder (bireysel gradyanlar GÖRÜNMEZ).
11. **Yeni global model yayınlama** (L2 → L3): IPFS'ye pin; zincire CID yaz.
12. **Tur sonu kaydı** (L3): `RoundOrchestrator.finalizeRound(roundId, newCID)`.

### 2.2 Uyarı Akışı (Faz 5)

1. Banka, yeni müşteri için federe embedding üretir (L1).
2. Embedding ile halka açık centroid'ler arasındaki mesafeyi hesaplar (L1).
3. Mesafe ≤ eşik ise `alert.circom` devresi ile ZK ispat üretir (L1).
4. `AlertVerifier.submitAlert(...)` zincir üstünde doğrulanır (L3).
5. `AlertRaised(centroid_id, round_id)` event'i yayılır (L3 → tüm bankalar).
6. Opsiyonel 314(b) opt-in: banka kendi `bankId`'sini açıklayabilir.
7. Diğer bankalar event'i izleyip kendi taraflarında benzer müşteri
   taramasını başlatır (yalnızca yerel).

---

## 3. Kritik Invariantlar

**INV-1** (CLAUDE.md Katı Kural #2): Ham işlem verisi hiçbir API üzerinden
dışarı çıkmaz. Statik test olarak `simulation/test_no_leakage.py` grep ile
doğrular.

**INV-2** (CLAUDE.md Katı Kural #3): Zincir üstü audit izleri deterministik
yeniden üretilebilir olmalı. `audit_replay.py` test'i her turun son
CID'sini yeniden hesaplar.

**INV-3**: Bir banka tek bir turda yalnızca bir kez katkı verebilir. Nullifier
= `H(bank_secret, round_id)` on-chain set'te unique.

**INV-4**: Toplayıcı hiçbir koşulda tek bir bankanın gradyan içeriğini
gözlemleyemez (SecAgg + DP). Testi: N=3 toplayıcıdan 1 kötü niyetli
simüle edilir; tek başına açamaz.

**INV-5**: Tüm sözleşmeler Slither ile temiz çıkmalı. CI bunu zorlar (Faz 7).

---

## 4. Teknoloji Seçim Gerekçesi

| Bileşen | Seçim | Gerekçe |
|---------|-------|---------|
| FL çatı | Flower | SecAgg+ stratejisi hazır, NumPyClient kolay |
| Graph model | GraphSAGE | Inductive — yeni müşteri, yeniden eğitim gerekmez |
| DP | Opacus | PyTorch native, RDP accountant dahil |
| ZK | Groth16 (Circom) | EVM doğrulayıcı ucuz (~250k gas) |
| L1 alternatifi | halo2 | Setup gerekmez ama EVM doğrulama pahalı → reddedildi |
| Blokzinciri | Besu IBFT 2.0 | Permissioned, EVM, finality < 5 sn |
| Depolama | IPFS | Content-addressed, hash bağlılığı doğal |
| Mesajlaşma | gRPC + TLS 1.3 | Proto ile tiplendirilmiş, streaming destekli |

---

## 5. Uygulama Sınırları (MVP)

- Hyperledger Besu tek-ağ; üretimde multi-region replika gerekebilir.
- Dashboard opsiyonel; Faz 7'de temel Grafana + hafif React.
- Kubernetes Faz 7'ye kadar zorunlu değil; Docker Compose yeterli.
- Donanım HSM entegrasyonu MVP'de placeholder; üretimde PKCS#11.
