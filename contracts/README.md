# contracts

Solidity 0.8.24 akıllı sözleşmeleri (Hyperledger Besu, IBFT 2.0, izinli ağ).

- `FedGuardRegistry.sol` — Faz 4: `submitProof`, `ContributionAccepted`, nullifier replay koruması
- `RoundOrchestrator.sol` — Faz 6: tur yaşam döngüsü, IPFS CID, global model hash
- `AuditLog.sol` — Faz 6: uyarılar için append-only log
- `AlertVerifier.sol` — Faz 5: mesafe ispatı doğrulayıcısı

Hardhat 2.22 ile build/deploy/test.
