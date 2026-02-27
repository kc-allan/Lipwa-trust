import crypto from "crypto";
import fs from "fs/promises";
import { Pool } from "pg";
import * as StellarSdk from "@stellar/stellar-sdk";
import { config } from "../config";
import { AppError } from "../utils/errors";
import { buildTransaction, signAndSubmit, sorobanRpc } from "./stellar";
import { getWalletPublicKey, getWalletSecret } from "./wallet";

const sdk: any = StellarSdk;
const pool = new Pool({ connectionString: config.databaseUrl });

interface ContractRecord {
  contract_id: string;
  merchant_wallet_id: string;
  supplier_wallet_id: string;
  amount: string;
}

export async function initContractTable(): Promise<void> {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS credit_contracts (
      contract_id TEXT PRIMARY KEY,
      merchant_wallet_id TEXT NOT NULL,
      supplier_wallet_id TEXT NOT NULL,
      amount TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  `);
}

function toScAddress(address: string): any {
  if (sdk.Address.fromString) {
    return sdk.Address.fromString(address);
  }
  return new sdk.Address(address);
}

function i128(value: bigint | number): any {
  return sdk.nativeToScVal(BigInt(value), { type: "i128" });
}

function u64(value: bigint | number): any {
  return sdk.nativeToScVal(BigInt(value), { type: "u64" });
}

function normalizeState(value: unknown): Record<string, unknown> {
  if (value instanceof Map) {
    return Object.fromEntries(value.entries());
  }

  if (typeof value === "object" && value !== null) {
    return value as Record<string, unknown>;
  }

  return {};
}

function normalizeStatus(status: unknown): string {
  if (Array.isArray(status)) {
    if (status.length === 0) {
      return "Unknown";
    }
    return normalizeStatus(status[0]);
  }

  if (typeof status === "string") {
    return status;
  }

  if (typeof status === "number") {
    const statuses = [
      "Created",
      "PendingDispatch",
      "Dispatched",
      "Delivered",
      "Repaying",
      "Disputed",
      "Cancelled",
      "Settled",
    ];
    return statuses[status] ?? "Unknown";
  }

  if (typeof status === "object" && status !== null) {
    const keys = Object.keys(status as Record<string, unknown>);
    if (keys.length > 0) {
      return keys[0];
    }
  }

  return "Unknown";
}

function toJsonSafe(value: unknown): unknown {
  if (typeof value === "bigint") {
    return value.toString();
  }

  if (Array.isArray(value)) {
    return value.map((item) => toJsonSafe(item));
  }

  if (value instanceof Map) {
    return Object.fromEntries(
      Array.from(value.entries(), ([key, mapValue]) => [String(key), toJsonSafe(mapValue)]),
    );
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, objectValue]) => [
        key,
        toJsonSafe(objectValue),
      ]),
    );
  }

  return value;
}

function toNumber(value: unknown): number {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "bigint") {
    return Number(value);
  }
  if (typeof value === "string") {
    const n = Number(value);
    return Number.isNaN(n) ? 0 : n;
  }
  return 0;
}

async function saveContractRecord(
  contractId: string,
  merchantWalletId: string,
  supplierWalletId: string,
  amount: number,
): Promise<void> {
  await pool.query(
    `INSERT INTO credit_contracts (contract_id, merchant_wallet_id, supplier_wallet_id, amount)
     VALUES ($1, $2, $3, $4)
     ON CONFLICT (contract_id) DO UPDATE SET
       merchant_wallet_id = EXCLUDED.merchant_wallet_id,
       supplier_wallet_id = EXCLUDED.supplier_wallet_id,
       amount = EXCLUDED.amount`,
    [contractId, merchantWalletId, supplierWalletId, String(amount)],
  );
}

async function getContractRecord(contractId: string): Promise<ContractRecord> {
  const result = await pool.query<ContractRecord>(
    `SELECT contract_id, merchant_wallet_id, supplier_wallet_id, amount
     FROM credit_contracts
     WHERE contract_id = $1`,
    [contractId],
  );

  if (result.rowCount === 0) {
    throw new AppError(`[CONTRACT] Contract record not found: ${contractId}`, 404);
  }

  return result.rows[0];
}

async function deployInventoryContract(): Promise<{ contractId: string; txHash: string }> {
  if (config.inventoryContractId) {
    return {
      contractId: config.inventoryContractId,
      txHash: "predeployed",
    };
  }

  if (!config.contractWasmPath) {
    throw new AppError(
      "Set INVENTORY_CONTRACT_ID or CONTRACT_WASM_PATH to deploy/invoke contracts",
      500,
    );
  }

  if (
    typeof sdk.Operation.uploadContractWasm !== "function" ||
    typeof sdk.Operation.createCustomContract !== "function"
  ) {
    throw new AppError(
      "Current Stellar SDK build does not expose contract deploy operations",
      500,
    );
  }

  const wasmBytes = await fs.readFile(config.contractWasmPath);
  const platformKeypair = sdk.Keypair.fromSecret(config.platformSecretKey);

  const uploadTx = await buildTransaction(platformKeypair.publicKey(), [
    sdk.Operation.uploadContractWasm({ wasm: wasmBytes }),
  ]);

  const uploadResult = await signAndSubmit(uploadTx, config.platformSecretKey);

  const wasmHashRaw = uploadResult.result?.returnValue
    ? sdk.scValToNative(uploadResult.result.returnValue)
    : null;

  if (!wasmHashRaw) {
    throw new AppError("Could not decode uploaded WASM hash from transaction", 500);
  }

  const wasmHash = Buffer.isBuffer(wasmHashRaw)
    ? wasmHashRaw
    : Buffer.from(wasmHashRaw);

  const deployTx = await buildTransaction(platformKeypair.publicKey(), [
    sdk.Operation.createCustomContract({
      address: toScAddress(platformKeypair.publicKey()).toScAddress(),
      wasmHash,
      salt: crypto.randomBytes(32),
    }),
  ]);

  const deployResult = await signAndSubmit(deployTx, config.platformSecretKey);

  const contractId =
    deployResult.result?.createdContractId ||
    (deployResult.result?.returnValue
      ? sdk.scValToNative(deployResult.result.returnValue)
      : null);

  if (!contractId || typeof contractId !== "string") {
    throw new AppError("Could not decode deployed contract ID", 500);
  }

  return {
    contractId,
    txHash: deployResult.txHash,
  };
}

async function invokeContract(
  contractId: string,
  method: string,
  args: any[],
  signerSecret: string,
): Promise<{ txHash: string; status: string; result: any }> {
  const signer = sdk.Keypair.fromSecret(signerSecret);
  const contract = new sdk.Contract(contractId);

  const tx = await buildTransaction(signer.publicKey(), [
    contract.call(method, ...args),
  ]);

  console.log(`[CONTRACT] invoke ${method} on ${contractId}`);

  return signAndSubmit(tx, signerSecret);
}

export async function getContractState(contractId: string): Promise<{
  contractId: string;
  status: string;
  amount: number;
  repaid: number;
  escrowBalance: number;
  raw: unknown;
}> {
  const platformKeypair = sdk.Keypair.fromSecret(config.platformSecretKey);
  const source = await sorobanRpc.getAccount(platformKeypair.publicKey());
  const contract = new sdk.Contract(contractId);

  const tx = new sdk.TransactionBuilder(source, {
    fee: sdk.BASE_FEE,
    networkPassphrase: config.networkPassphrase,
  })
    .addOperation(contract.call("get_state"))
    .setTimeout(30)
    .build();

  const simulation = await sorobanRpc.simulateTransaction(tx);
  if ("error" in simulation) {
    throw new AppError(
      `[CONTRACT] Simulation failed for ${contractId}: ${simulation.error}`,
      500,
    );
  }

  const retval = "result" in simulation ? simulation.result?.retval : undefined;

  if (!retval) {
    throw new AppError(`[CONTRACT] Could not fetch state for ${contractId}`, 500);
  }

  const nativeRaw = sdk.scValToNative(retval);
  const state = normalizeState(nativeRaw);

  const amount = toNumber(state.amount);
  const repaid = toNumber(state.repaid);
  const escrowBalance = toNumber(state.escrow_balance ?? state.escrowBalance);

  return {
    contractId,
    status: normalizeStatus(state.status),
    amount,
    repaid,
    escrowBalance,
    raw: toJsonSafe(nativeRaw),
  };
}

export async function createCreditContract(input: {
  merchantWalletId: string;
  supplierWalletId: string;
  amount: number;
  dispatchDeadlineHours: number;
}): Promise<{ contractId: string; stellarTxHash: string; status: string }> {
  const { merchantWalletId, supplierWalletId, amount, dispatchDeadlineHours } = input;

  if (amount <= 0) {
    throw new AppError("amount must be positive", 400);
  }

  if (!config.kesxTokenContractId) {
    throw new AppError("KESX_TOKEN_CONTRACT_ID is not configured", 500);
  }

  const merchantPublicKey = await getWalletPublicKey(merchantWalletId);
  const supplierPublicKey = await getWalletPublicKey(supplierWalletId);
  const platformPublicKey = sdk.Keypair.fromSecret(
    config.platformSecretKey,
  ).publicKey();

  const { contractId } = await deployInventoryContract();
  const dispatchDeadline = Math.floor(Date.now() / 1000) + dispatchDeadlineHours * 3600;

  const createResult = await invokeContract(
    contractId,
    "create",
    [
      toScAddress(merchantPublicKey).toScVal(),
      toScAddress(supplierPublicKey).toScVal(),
      toScAddress(platformPublicKey).toScVal(),
      i128(amount),
      toScAddress(config.kesxTokenContractId).toScVal(),
      u64(dispatchDeadline),
    ],
    config.platformSecretKey,
  );

  await saveContractRecord(contractId, merchantWalletId, supplierWalletId, amount);

  const state = await getContractState(contractId);

  return {
    contractId,
    stellarTxHash: createResult.txHash,
    status: state.status,
  };
}

export async function fundEscrow(
  contractId: string,
  fromWalletId: string,
  amount: number,
): Promise<{ txHash: string; escrowBalance: number }> {
  const fromPublicKey = await getWalletPublicKey(fromWalletId);
  const fromSecret = await getWalletSecret(fromWalletId);

  const result = await invokeContract(
    contractId,
    "fund_escrow",
    [toScAddress(fromPublicKey).toScVal(), i128(amount)],
    fromSecret,
  );

  const state = await getContractState(contractId);

  return {
    txHash: result.txHash,
    escrowBalance: state.escrowBalance,
  };
}

export async function dispatchGoods(
  contractId: string,
  supplierWalletId: string,
): Promise<{ txHash: string; status: string }> {
  const supplierSecret = await getWalletSecret(supplierWalletId);
  const result = await invokeContract(contractId, "dispatch", [], supplierSecret);
  const state = await getContractState(contractId);

  return {
    txHash: result.txHash,
    status: state.status,
  };
}

export async function confirmDelivery(
  contractId: string,
  merchantWalletId: string,
): Promise<{ txHash: string; status: string; supplierPayout: number }> {
  const merchantSecret = await getWalletSecret(merchantWalletId);
  const before = await getContractState(contractId);

  const result = await invokeContract(contractId, "deliver", [], merchantSecret);
  const after = await getContractState(contractId);

  return {
    txHash: result.txHash,
    status: after.status,
    supplierPayout: before.escrowBalance,
  };
}

export async function recordRepayment(
  contractId: string,
  amount: number,
): Promise<{ txHash: string; repaid: number; remaining: number }> {
  const result = await invokeContract(
    contractId,
    "record_repayment",
    [i128(amount)],
    config.platformSecretKey,
  );

  const state = await getContractState(contractId);
  return {
    txHash: result.txHash,
    repaid: state.repaid,
    remaining: Math.max(0, state.amount - state.repaid),
  };
}

export async function settleContract(
  contractId: string,
): Promise<{ txHash: string; status: string }> {
  const result = await invokeContract(
    contractId,
    "settle",
    [],
    config.platformSecretKey,
  );

  const state = await getContractState(contractId);

  return {
    txHash: result.txHash,
    status: state.status,
  };
}

export async function raiseDispute(
  contractId: string,
  reason: string,
  raisedBy: string,
): Promise<{ txHash: string; status: string }> {
  let signerSecret = config.platformSecretKey;
  let raisedByPublicKey = sdk.Keypair.fromSecret(config.platformSecretKey).publicKey();

  if (raisedBy !== "platform") {
    if (raisedBy === "merchant") {
      const record = await getContractRecord(contractId);
      signerSecret = await getWalletSecret(record.merchant_wallet_id);
      raisedByPublicKey = await getWalletPublicKey(record.merchant_wallet_id);
    } else {
      signerSecret = await getWalletSecret(raisedBy);
      raisedByPublicKey = await getWalletPublicKey(raisedBy);
    }
  }

  const result = await invokeContract(
    contractId,
    "raise_dispute",
    [
      sdk.nativeToScVal(reason, { type: "string" }),
      toScAddress(raisedByPublicKey).toScVal(),
    ],
    signerSecret,
  );

  const state = await getContractState(contractId);

  return {
    txHash: result.txHash,
    status: state.status,
  };
}

export async function cancelContract(
  contractId: string,
): Promise<{ txHash: string; refundAmount: number; status: string }> {
  const before = await getContractState(contractId);

  const result = await invokeContract(
    contractId,
    "cancel",
    [],
    config.platformSecretKey,
  );

  const after = await getContractState(contractId);

  return {
    txHash: result.txHash,
    refundAmount: before.escrowBalance,
    status: after.status,
  };
}

export async function closeContractPool(): Promise<void> {
  await pool.end();
}
