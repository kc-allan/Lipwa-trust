# 🔗 Lipwa-Trust — Blockchain Component

The blockchain layer for the Lipwa-Trust inventory financing platform. It provides on-chain settlement, escrow management, and audit logging via **Stellar Soroban** smart contracts, exposed through a **TypeScript HTTP oracle API**.

---

## Architecture

```
Backend (NestJS)  ──HTTP──▶  Oracle API (TypeScript/Express)  ──Stellar SDK──▶  Soroban Smart Contract (Stellar Testnet)
```

| Layer              | Description                                                                                                                                              |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Smart Contract** | Rust/Soroban contract managing the inventory credit lifecycle: escrow, state transitions, repayment tracking, dispute handling, and audit event emission |
| **Oracle API**     | TypeScript + Express HTTP server that wraps Stellar SDK calls, manages wallets, and exposes contract operations as REST endpoints for the backend        |
| **Wallet Manager** | Server-side Stellar keypair generation and secure storage in PostgreSQL                                                                                  |

---

## Smart Contract Lifecycle

```
CREATED → PENDING_DISPATCH → DISPATCHED → DELIVERED → REPAYING → SETTLED
                  │
                  └── DISPUTED → CANCELLED (with escrow refund)
```

Each state transition emits an on-chain audit event queryable via Horizon API.

---

## Project Structure

```
blockchain/
├── contracts/                     # Soroban smart contracts (Rust)
│   └── inventory_credit/
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs             # Contract logic + state machine
│           └── test.rs            # On-chain unit tests
├── oracle/                        # TypeScript HTTP oracle
│   ├── package.json
│   ├── tsconfig.json
│   ├── .env.example
│   └── src/
│       ├── index.ts               # Express entry point
│       ├── config.ts              # Stellar network configuration
│       ├── routes/
│       │   ├── wallets.ts         # Wallet creation & retrieval
│       │   └── contracts.ts       # Contract interaction endpoints
│       ├── services/
│       │   ├── stellar.ts         # Stellar SDK wrapper
│       │   ├── wallet.ts          # Keypair generation + DB ops
│       │   ├── contract.ts        # Contract deployment + invocation
│       │   └── events.ts          # Horizon event queries
│       ├── models/
│       │   └── wallet.ts          # Wallet DB model
│       └── utils/
│           ├── keypair.ts         # Keypair helpers
│           └── errors.ts          # Error types
├── PLAN.md                        # Detailed implementation plan
└── README.md                      # This file
```

---

## Tech Stack

| Technology       | Purpose                                | Version       |
| ---------------- | -------------------------------------- | ------------- |
| Rust             | Smart contract language (Soroban)      | Latest stable |
| Soroban SDK      | Soroban contract development           | v20.4.0       |
| Stellar SDK (JS) | Blockchain interaction from TypeScript | v14.5.0       |
| TypeScript       | Oracle API language                    | Latest        |
| Express          | Oracle HTTP framework                  | Latest        |
| PostgreSQL       | Wallet storage (shared with backend)   | —             |

---

## Dockerization Advice

For this module, dockerize the **runtime components**:

- **Oracle API** (Express service)
- **PostgreSQL** (wallet/contract metadata storage)

The **smart contract** is not a long-running service; it is a build/deploy artifact.  
Keep it as a CLI-driven flow (local or CI), and have the Oracle call an already deployed `INVENTORY_CONTRACT_ID` in day-to-day runs.

---

## Prerequisites

1. **Rust & Soroban CLI**

   ```bash
   # Install Rust
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   rustup target add wasm32v1-none

   # Install Soroban CLI
   cargo install --locked soroban-cli
   ```

2. **Stellar CLI** (optional, usually comes with Soroban CLI, but can be installed separately)

   ```bash
   cargo install --locked stellar-cli
   ```

3. **Node.js** (v18+) for the oracle API
4. **PostgreSQL** running locally or via Docker

---

## Getting Started

### 0. Run Oracle + DB in Docker (recommended local runtime)

```bash
cd blockchain

# First time only: create oracle env file
cp oracle/.env.example oracle/.env
# Edit oracle/.env and set real PLATFORM_SECRET_KEY, KESX_TOKEN_CONTRACT_ID, etc.

# Start oracle + postgres
docker compose up --build -d

# Logs / stop
docker compose logs -f oracle
docker compose down
```

Notes:
- Oracle will be available on `http://localhost:3001`
- Postgres is exposed on `localhost:5433` (container-internal port remains `5432`)
- In Docker mode, `DATABASE_URL` is automatically set to use the `postgres` service
- `contracts/` is mounted read-only into the Oracle container at `/contracts`
- If you want create endpoint to deploy from wasm (instead of using `INVENTORY_CONTRACT_ID`), build contract first so this file exists:
  `/contracts/inventory_credit/target/wasm32v1-none/release/inventory_credit.wasm`

### 1. Smart Contract

```bash
cd blockchain/contracts/inventory_credit

# Build
soroban contract build

# Run tests
cargo test

# Deploy to testnet
soroban contract deploy \
  --wasm target/wasm32v1-none/release/inventory_credit.wasm \
  --network testnet \
  --source <PLATFORM_SECRET_KEY>
```

### 2. Oracle API (without Docker)

```bash
cd blockchain/oracle

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your testnet keys and database URL

# Run in development mode
npm run dev
# Oracle runs on http://localhost:3001
```

### 3. Postman Collection
Import the provided [Postman Collection](./oracle/postman/lipwa-trust-oracle.postman_collection.json) and [Postman Environment](./oracle/postman/lipwa-trust-oracle.postman_environment.json) into Postman to access and test pre-configured requests for all oracle API endpoints, including contract creation, funding, state transitions, and event queries.

### 4. Test Asset Setup

Before running the full flow, issue the `KESX` test asset:

```bash
# (Automated via oracle startup or a setup script)
# 1. Create issuer account on testnet
# 2. Issue KESX asset
# 3. Establish trustlines for all accounts
# 4. Mint KESX to platform account
```

---

## API Reference

### Wallets

| Method | Endpoint          | Description                         |
| ------ | ----------------- | ----------------------------------- |
| `POST` | `/wallets/create` | Create a new Stellar testnet wallet |
| `GET`  | `/wallets/:id`    | Get wallet public key and metadata  |

### Contracts

| Method | Endpoint                  | Description                                  |
| ------ | ------------------------- | -------------------------------------------- |
| `POST` | `/contracts/create`       | Deploy a new inventory credit contract       |
| `POST` | `/contracts/:id/fund`     | Fund the contract's escrow                   |
| `POST` | `/contracts/:id/dispatch` | Supplier confirms goods dispatched           |
| `POST` | `/contracts/:id/deliver`  | Merchant confirms delivery (triggers payout) |
| `POST` | `/contracts/:id/repay`    | Record a repayment installment               |
| `POST` | `/contracts/:id/settle`   | Finalize a fully-repaid contract             |
| `POST` | `/contracts/:id/dispute`  | Raise a dispute                              |
| `POST` | `/contracts/:id/cancel`   | Cancel contract and refund escrow            |
| `GET`  | `/contracts/:id/status`   | Get current contract state                   |
| `GET`  | `/contracts/:id/events`   | Get audit event log                          |

---

## Environment Variables

| Variable              | Description                  | Example                                       |
| --------------------- | ---------------------------- | --------------------------------------------- |
| `STELLAR_NETWORK`     | Network to use               | `testnet`                                     |
| `SOROBAN_RPC_URL`     | Soroban RPC endpoint         | `https://soroban-testnet.stellar.org`         |
| `HORIZON_URL`         | Horizon API endpoint         | `https://horizon-testnet.stellar.org`         |
| `FRIENDBOT_URL`       | Testnet funding endpoint     | `https://friendbot.stellar.org`               |
| `PLATFORM_SECRET_KEY` | Platform account secret key  | `S...`                                        |
| `DATABASE_URL`        | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/lipwa` |
| `PORT`                | Oracle API port              | `3001`                                        |

---

## Verification

### Smart Contract Tests

```bash
cd blockchain/contracts/inventory_credit
cargo test
```

- Happy path: full lifecycle from creation to settlement
- Dispute path: dispute raised and contract cancelled with refund
- Invalid transitions: rejected with errors
- Authorization checks: only authorized callers can trigger transitions

### Oracle API Manual Tests

See the full curl-based test sequence in [PLAN.md](./PLAN.md#82-oracle-api-tests-manual--curl).

### Visual Verification

Open the deployed contract on [Stellar Expert (testnet)](https://stellar.expert/explorer/testnet) to verify transactions and events.

---

## Mainnet Considerations

> **Not in scope for the hackathon**, but the architecture is designed with these future requirements in mind:

- Encrypted keypair storage (AES-256 + KMS/HSM)
- Regulated stablecoin integration (replacing `KESX` test asset)
- XLM fee management and funding pool
- Multi-sig dispute resolution with independent arbiter
- Rate limiting and authentication on the oracle API
- Monitoring and alerting (Prometheus/Grafana)
- Soroban contract upgrade mechanisms
