import { sorobanRpc } from "./stellar";

export interface ContractEventResponse {
  event: string;
  timestamp: string;
  data: unknown;
}

const DEFAULT_EVENT_LOOKBACK_LEDGERS = 50_000;

function parseLedgerRangeFromError(error: unknown): {
  oldestLedger: number;
  latestLedger: number;
} | null {
  const message =
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof (error as { message?: unknown }).message === "string"
      ? (error as { message: string }).message
      : error instanceof Error
        ? error.message
        : "";

  const match = message.match(/ledger range:\s*(\d+)\s*-\s*(\d+)/i);
  if (!match) {
    return null;
  }

  const oldestLedger = Number(match[1]);
  const latestLedger = Number(match[2]);

  if (Number.isNaN(oldestLedger) || Number.isNaN(latestLedger)) {
    return null;
  }

  return { oldestLedger, latestLedger };
}

export async function getContractEvents(
  contractId: string,
): Promise<ContractEventResponse[]> {
  const latestLedger = await sorobanRpc.getLatestLedger();
  const lookbackRaw = Number(process.env.EVENT_LOOKBACK_LEDGERS ?? DEFAULT_EVENT_LOOKBACK_LEDGERS);
  const lookback =
    Number.isFinite(lookbackRaw) && lookbackRaw > 0
      ? Math.floor(lookbackRaw)
      : DEFAULT_EVENT_LOOKBACK_LEDGERS;

  const requestBase = {
    filters: [
      {
        type: "contract" as const,
        contractIds: [contractId],
      },
    ],
    limit: 100,
  };

  const initialStartLedger = Math.max(1, latestLedger.sequence - lookback + 1);

  let eventsResult: any;

  try {
    eventsResult = await sorobanRpc.getEvents({
      ...requestBase,
      startLedger: initialStartLedger,
      endLedger: latestLedger.sequence,
    });
  } catch (error) {
    const range = parseLedgerRangeFromError(error);
    if (!range) {
      throw error;
    }

    eventsResult = await sorobanRpc.getEvents({
      ...requestBase,
      startLedger: range.oldestLedger,
      endLedger: range.latestLedger,
    });
  }

  const events = eventsResult.events ?? [];

  return events.map((entry: any) => ({
    event: entry.topic?.join(":") ?? "audit",
    timestamp: entry.ledgerClosedAt ?? new Date().toISOString(),
    data: entry.value ?? entry,
  }));
}
