# aggregator

Toplama komitesi (n=3, BFT) — bireysel gradyanları asla göremez.

- Flower sunucusu + SecAgg+ (`server.py`) — Faz 3
- DWFL ağırlıklandırma stratejisi — Faz 3
- Groth16 zincir-dışı doğrulayıcı — Faz 4
- Audit replay aracı (`audit_replay.py`) — Faz 6

Komite, Byzantine fault-tolerant olacak şekilde 3 düğümden oluşur; herhangi bir tek toplayıcı gradyan maskelerini açamaz.
