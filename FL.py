"""
Federated Learning Framework
=============================
Modüler ve genişletilebilir bir Federated Learning altyapısı.

Desteklenen özellikler:
  - FedAvg (Federated Averaging) algoritması
  - IID ve Non-IID veri dağılımı
  - Differential Privacy (DP) desteği
  - Özelleştirilebilir model, dataset ve aggregation stratejileri
  - Detaylı loglama ve metrik takibi

Kullanım:
  python FL.py
"""

import copy
import random
import logging
from collections import OrderedDict
from typing import List, Dict, Tuple, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset, Subset
from torchvision import datasets, transforms

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("FL")


# ═════════════════════════════════════════════
# 1. MODEL TANIMLARI
# ═════════════════════════════════════════════
class CNNModel(nn.Module):
    """MNIST / Fashion-MNIST için basit CNN modeli."""

    def __init__(self, num_classes: int = 10):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.5)
        self.fc1 = nn.Linear(64 * 7 * 7, 128)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = self.dropout1(x)
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        x = self.dropout2(x)
        return self.fc2(x)


class MLPModel(nn.Module):
    """Basit MLP modeli – hızlı test için."""

    def __init__(self, input_dim: int = 784, num_classes: int = 10):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x.view(x.size(0), -1))


# ═════════════════════════════════════════════
# 2. VERİ DAĞITIMI (IID & Non-IID)
# ═════════════════════════════════════════════
def distribute_iid(dataset: Dataset, num_clients: int) -> Dict[int, List[int]]:
    """Veriyi client'lara eşit ve rastgele (IID) dağıtır."""
    indices = list(range(len(dataset)))
    random.shuffle(indices)
    shard_size = len(indices) // num_clients
    return {
        i: indices[i * shard_size : (i + 1) * shard_size]
        for i in range(num_clients)
    }


def distribute_non_iid(
    dataset: Dataset, num_clients: int, shards_per_client: int = 2
) -> Dict[int, List[int]]:
    """
    Non-IID dağılım: veriyi label'a göre sıralar,
    shard'lara böler ve her client'a belirli shard'lar verir.
    """
    targets = np.array([dataset[i][1] for i in range(len(dataset))])
    sorted_indices = np.argsort(targets).tolist()

    total_shards = num_clients * shards_per_client
    shard_size = len(sorted_indices) // total_shards
    shards = [
        sorted_indices[i * shard_size : (i + 1) * shard_size]
        for i in range(total_shards)
    ]

    random.shuffle(shards)
    client_data: Dict[int, List[int]] = {}
    for i in range(num_clients):
        selected = shards[i * shards_per_client : (i + 1) * shards_per_client]
        client_data[i] = [idx for shard in selected for idx in shard]
    return client_data


# ═════════════════════════════════════════════
# 3. CLIENT
# ═════════════════════════════════════════════
class FLClient:
    """Federated Learning client'ı – lokal eğitim yapar."""

    def __init__(
        self,
        client_id: int,
        dataset: Dataset,
        indices: List[int],
        batch_size: int = 32,
        local_epochs: int = 5,
        lr: float = 0.01,
        device: str = "cpu",
        dp_enabled: bool = False,
        dp_clip_norm: float = 1.0,
        dp_noise_scale: float = 0.1,
    ):
        self.client_id = client_id
        self.device = device
        self.local_epochs = local_epochs
        self.lr = lr
        self.dp_enabled = dp_enabled
        self.dp_clip_norm = dp_clip_norm
        self.dp_noise_scale = dp_noise_scale

        subset = Subset(dataset, indices)
        self.loader = DataLoader(subset, batch_size=batch_size, shuffle=True)
        self.data_size = len(indices)

    def train(self, global_model: nn.Module) -> Tuple[OrderedDict, int, float]:
        """
        Global modeli alır, lokal olarak eğitir ve güncellenmiş
        ağırlıkları döndürür.

        Returns:
            (state_dict, data_size, avg_loss)
        """
        model = copy.deepcopy(global_model).to(self.device)
        model.train()
        optimizer = torch.optim.SGD(model.parameters(), lr=self.lr, momentum=0.9)
        criterion = nn.CrossEntropyLoss()

        total_loss = 0.0
        total_samples = 0

        for epoch in range(self.local_epochs):
            for data, target in self.loader:
                data, target = data.to(self.device), target.to(self.device)
                optimizer.zero_grad()
                output = model(data)
                loss = criterion(output, target)
                loss.backward()

                # Differential Privacy: gradient clipping
                if self.dp_enabled:
                    nn.utils.clip_grad_norm_(model.parameters(), self.dp_clip_norm)

                optimizer.step()
                total_loss += loss.item() * data.size(0)
                total_samples += data.size(0)

        avg_loss = total_loss / max(total_samples, 1)

        # Differential Privacy: ağırlıklara gürültü ekle
        state_dict = model.state_dict()
        if self.dp_enabled:
            state_dict = self._add_noise(state_dict)

        return state_dict, self.data_size, avg_loss

    def _add_noise(self, state_dict: OrderedDict) -> OrderedDict:
        """DP için model ağırlıklarına Gaussian gürültü ekler."""
        noisy = OrderedDict()
        for key, param in state_dict.items():
            noise = torch.randn_like(param) * self.dp_noise_scale
            noisy[key] = param + noise
        return noisy


# ═════════════════════════════════════════════
# 4. AGGREGATION STRATEJİLERİ
# ═════════════════════════════════════════════
def fedavg_aggregate(
    client_results: List[Tuple[OrderedDict, int, float]],
) -> OrderedDict:
    """
    FedAvg: client ağırlıklarını veri miktarına göre
    ağırlıklı ortalama ile birleştirir.
    """
    total_data = sum(size for _, size, _ in client_results)
    aggregated = OrderedDict()

    for key in client_results[0][0].keys():
        aggregated[key] = sum(
            (result[key].float() * (size / total_data))
            for result, size, _ in client_results
        )

    return aggregated


# ═════════════════════════════════════════════
# 5. SERVER (Orchestrator)
# ═════════════════════════════════════════════
class FLServer:
    """
    Federated Learning sunucusu.
    Client'ları koordine eder, aggregation yapar, değerlendirir.
    """

    def __init__(
        self,
        model: nn.Module,
        test_dataset: Dataset,
        num_clients: int = 10,
        fraction_fit: float = 1.0,
        num_rounds: int = 20,
        batch_size: int = 32,
        local_epochs: int = 5,
        lr: float = 0.01,
        iid: bool = True,
        device: str = "cpu",
        dp_enabled: bool = False,
        dp_clip_norm: float = 1.0,
        dp_noise_scale: float = 0.1,
    ):
        self.global_model = model.to(device)
        self.device = device
        self.num_clients = num_clients
        self.fraction_fit = fraction_fit
        self.num_rounds = num_rounds
        self.batch_size = batch_size
        self.local_epochs = local_epochs
        self.lr = lr
        self.dp_enabled = dp_enabled
        self.dp_clip_norm = dp_clip_norm
        self.dp_noise_scale = dp_noise_scale

        self.test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)
        self.history: Dict[str, List[float]] = {
            "round_loss": [],
            "accuracy": [],
            "test_loss": [],
        }

        # İID seçimi
        self.iid = iid

    def _select_clients(self, clients: List[FLClient]) -> List[FLClient]:
        """Her round'da katılacak client alt kümesini seçer."""
        num_selected = max(1, int(len(clients) * self.fraction_fit))
        return random.sample(clients, num_selected)

    def evaluate(self) -> Tuple[float, float]:
        """Global modeli test seti üzerinde değerlendirir."""
        self.global_model.eval()
        test_loss = 0.0
        correct = 0
        total = 0
        criterion = nn.CrossEntropyLoss()

        with torch.no_grad():
            for data, target in self.test_loader:
                data, target = data.to(self.device), target.to(self.device)
                output = self.global_model(data)
                test_loss += criterion(output, target).item() * data.size(0)
                pred = output.argmax(dim=1)
                correct += pred.eq(target).sum().item()
                total += target.size(0)

        accuracy = correct / total
        avg_loss = test_loss / total
        return accuracy, avg_loss

    def run(self, train_dataset: Dataset):
        """Federated Learning eğitim döngüsünü başlatır."""
        logger.info("=" * 60)
        logger.info("  FEDERATED LEARNING BAŞLATILIYOR")
        logger.info(f"  Client sayısı    : {self.num_clients}")
        logger.info(f"  Round sayısı     : {self.num_rounds}")
        logger.info(f"  Veri dağılımı    : {'IID' if self.iid else 'Non-IID'}")
        logger.info(f"  Lokal epoch      : {self.local_epochs}")
        logger.info(f"  Learning rate    : {self.lr}")
        logger.info(f"  Differential Privacy : {'Açık' if self.dp_enabled else 'Kapalı'}")
        logger.info(f"  Device           : {self.device}")
        logger.info("=" * 60)

        # Veriyi client'lara dağıt
        if self.iid:
            client_data = distribute_iid(train_dataset, self.num_clients)
        else:
            client_data = distribute_non_iid(train_dataset, self.num_clients)

        # Client nesnelerini oluştur
        clients = [
            FLClient(
                client_id=i,
                dataset=train_dataset,
                indices=client_data[i],
                batch_size=self.batch_size,
                local_epochs=self.local_epochs,
                lr=self.lr,
                device=self.device,
                dp_enabled=self.dp_enabled,
                dp_clip_norm=self.dp_clip_norm,
                dp_noise_scale=self.dp_noise_scale,
            )
            for i in range(self.num_clients)
        ]

        # ─── Eğitim Döngüsü ───
        for round_num in range(1, self.num_rounds + 1):
            logger.info(f"─── Round {round_num}/{self.num_rounds} ───")

            selected = self._select_clients(clients)
            client_results = []

            for client in selected:
                state_dict, data_size, loss = client.train(self.global_model)
                client_results.append((state_dict, data_size, loss))
                logger.debug(
                    f"  Client {client.client_id}: loss={loss:.4f}, "
                    f"samples={data_size}"
                )

            # Aggregation
            avg_loss = np.mean([loss for _, _, loss in client_results])
            aggregated_weights = fedavg_aggregate(client_results)
            self.global_model.load_state_dict(aggregated_weights)

            # Değerlendirme
            accuracy, test_loss = self.evaluate()

            self.history["round_loss"].append(avg_loss)
            self.history["accuracy"].append(accuracy)
            self.history["test_loss"].append(test_loss)

            logger.info(
                f"  Ortalama Loss: {avg_loss:.4f} │ "
                f"Test Loss: {test_loss:.4f} │ "
                f"Accuracy: {accuracy * 100:.2f}%"
            )

        logger.info("=" * 60)
        logger.info(f"  EĞİTİM TAMAMLANDI")
        logger.info(f"  Son Accuracy: {self.history['accuracy'][-1] * 100:.2f}%")
        logger.info("=" * 60)

        return self.history


# ═════════════════════════════════════════════
# 6. YARDIMCI FONKSİYONLAR
# ═════════════════════════════════════════════
def get_device() -> str:
    """Kullanılabilir en iyi cihazı döndürür."""
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_mnist() -> Tuple[Dataset, Dataset]:
    """MNIST veri setini indirir ve döndürür."""
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])
    train = datasets.MNIST("./data", train=True, download=True, transform=transform)
    test = datasets.MNIST("./data", train=False, download=True, transform=transform)
    return train, test


def load_fashion_mnist() -> Tuple[Dataset, Dataset]:
    """Fashion-MNIST veri setini indirir ve döndürür."""
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.2860,), (0.3530,)),
    ])
    train = datasets.FashionMNIST(
        "./data", train=True, download=True, transform=transform
    )
    test = datasets.FashionMNIST(
        "./data", train=False, download=True, transform=transform
    )
    return train, test


# ═════════════════════════════════════════════
# 7. ANA ÇALIŞTIRMA
# ═════════════════════════════════════════════
def main():
    """Federated Learning demo çalıştırması."""
    device = get_device()
    logger.info(f"Device: {device}")

    # ── Konfigürasyon ──
    config = {
        "num_clients": 10,
        "num_rounds": 10,
        "fraction_fit": 0.5,       # Her round'da client'ların %50'si katılır
        "batch_size": 32,
        "local_epochs": 3,
        "lr": 0.01,
        "iid": True,              # False → Non-IID dağılım
        "dp_enabled": False,      # True → Differential Privacy
        "dp_clip_norm": 1.0,
        "dp_noise_scale": 0.01,
    }

    # ── Veri Seti ──
    train_dataset, test_dataset = load_mnist()

    # ── Model ──
    model = CNNModel(num_classes=10)

    # ── Server ──
    server = FLServer(
        model=model,
        test_dataset=test_dataset,
        device=device,
        **config,
    )

    # ── Eğitim ──
    history = server.run(train_dataset)

    # ── Sonuçları kaydet ──
    torch.save(server.global_model.state_dict(), "fl_global_model.pth")
    logger.info("Model kaydedildi: fl_global_model.pth")


if __name__ == "__main__":
    main()
