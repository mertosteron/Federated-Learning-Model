# bank-node

Her banka kendi VPC'sinde çalıştıracağı düğüm. Bu dizin:

- Yerel işlem grafiği inşası (`graph_builder.py`) — Faz 1
- GraphSAGE modeli (`model.py`) — Faz 2
- DP-SGD ile yerel eğitim (`train_local.py`) — Faz 2
- Flower FL istemcisi (`fl_client.py`) — Faz 3
- ZK prover istemcisi (`prover.py`) — Faz 4

Ham veri **hiçbir koşulda** bu dizinin dışına çıkmaz. Yalnızca gradyanlar + ispatlar gider.
