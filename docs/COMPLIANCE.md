# FedGuard — Düzenleyici Uyum Haritası

**Sürüm:** 0.1 (Faz 0)
**Son güncelleme:** 2026-04-23

Bu belge, FedGuard mimarisinin Banka Gizliliği Yasası (BSA), FATF Tavsiyeleri,
GDPR ve FinCEN 314(b) gereksinimlerini nasıl karşıladığını listeler. Her fazın
sonunda güncellenir (CLAUDE.md §6).

---

## 1. Uyum Matrisi

| Düzenleme | Gereksinim | Bu sistem nasıl karşılıyor? | Kanıt konumu |
|---|---|---|---|
| **BSA §5318(h)** | AML programı, risk-bazlı tespit | Federe GNN kurumlar arası halka tespiti + DWFL doğruluk-ağırlıklı toplama | `aggregator/server.py` (Faz 3), `audit_replay.py` (Faz 6) |
| **BSA §5318(g) — SAR zorunluluğu** | Şüpheli faaliyet raporlaması | Zincir üstü `AlertRaised` event'i banka içi SAR tetikleyicisi; her uyarı için nullifier kaydı | `contracts/AuditLog.sol` (Faz 6), `contracts/AlertVerifier.sol` (Faz 5) |
| **BSA §5312 — CIP/KYC** | Müşteri kimlik programı | Yerel, banka içinde kalır; federasyona dahil değildir | `bank-node/*` (Faz 1 — dışa akış yok) |
| **FATF Tavsiye 10** | Müşteri durum tespiti (CDD) | Aynı BSA CIP/KYC ile karşılanır; veri yerel | `bank-node/` |
| **FATF Tavsiye 11** | Kayıt tutma (5 yıl) | Zincir üstü audit log değiştirilemez; IPFS pin'leri 5 yıl süreli politika ile tutulur | `contracts/AuditLog.sol`, IPFS pinning policy |
| **FATF Tavsiye 13 — muhabir bankacılık** | Sınır ötesi işlem kontrolü | Federe model sınır ötesi halka tespitini mümkün kılar | Faz 3/5 |
| **FATF Tavsiye 16 — havale bilgisi** | Havale kurucu bilgisi | ZK uyarısı yalnızca centroid mesafesini içerir; PII içermez | `circuits/alert.circom` (Faz 5) |
| **FATF Tavsiye 20 — STR** | Şüpheli işlem bildirimi | `AlertRaised` event'i SAR akışını başlatır | Faz 5 |
| **GDPR Madde 22** | Otomatik karar verme hakkı | Uyarılar **karar değildir**; insan-döngüde review `dashboard/` üzerinden zorunlu | Faz 7 operatör UI |
| **GDPR Madde 25** | Tasarım gereği gizlilik | DP-SGD, SecAgg, ZK hepsi mimaride yerleşik | THREAT_MODEL.md §4 |
| **GDPR Madde 5 — veri minimizasyonu** | Gerekli minimum veri | Gradyan + ispat dışında hiçbir şey yerelden çıkmaz | `bank-node/fl_client.py` (Faz 3) |
| **GDPR Madde 32 — güvenlik** | Uygun teknik önlemler | mTLS, DP, SecAgg, ZK — THREAT_MODEL.md'de STRIDE eşleşmeli | Faz 3-4 |
| **FinCEN 314(b)** | Gönüllü kurumlar arası paylaşım | Zincir üstü opt-in event'ler; banka `AlertRaised`'i opt-in olarak kendi `bankId` ile açabilir | Faz 5, Faz 6 |
| **FinCEN CDD Final Rule** | Gerçek hak sahipliği | Yerel; federasyon dışında | `bank-node/` |

---

## 2. Kanıt Defteri (Evidence Ledger)

Denetçi için:

1. **Tüm zincir üstü event'ler** Besu'dan çekilebilir ve `audit_replay.py` ile
   yeniden üretilebilir.
2. **IPFS CID'leri** üzerinden her tur global modeli byte-bayt yeniden
   sağlanabilir.
3. **ZK ispat verifikasyon kayıtları** `FedGuardRegistry.sol` üzerinden
   sorgulanabilir.
4. **DP bütçesi tüketimi** tur başına Grafana panosunda ve `round_metadata`
   event'lerinde kayıtlıdır.
5. **Katılım nullifier'ları** replay ve Sybil saldırılarını dışlar.

---

## 3. Açık Konular / Üretim Öncesi Zorunluluklar

- [ ] Trusted setup (Faz 4) MPC seremonisi — MVP'de tek taraflı, üretim için
  çok-taraflı zorunlu.
- [ ] Bağımsız kriptografi denetimi (Faz 7 sonrası).
- [ ] Red-team testi — özellikle gradyan yan-kanal zamanlama.
- [ ] Yerel düzenleyici (BDDK / FinCEN / FCA) ön-görüşme.
- [ ] Veri İşleme Sözleşmesi (DPA) şablonu — her katılımcı banka ile imzalanmalı.
- [ ] Yetki / olay müdahale rehberi (Incident Response Plan).

---

## 4. Düzenleyici Erişim Modeli

| Rol | Read Access | Write Access |
|-----|-------------|--------------|
| Denetçi (BSA, FATF) | Zincir üstü tüm event'ler, IPFS CID'leri, model ağırlıkları | — |
| Banka compliance ofisi | Kendi SAR tetikleyicileri + zincir üstü event'ler | Kendi `AlertRaised` decloak opt-in |
| FinCEN 314(b) katılımcıları | Diğer opt-in bankaların `AlertRaised` metadata'sı | Kendi opt-in kayıtları |
| Kamu / 3. taraf | — | — |

Hiçbir rolün ham PII'ye erişimi yoktur.
