import { Router } from "express";
import {
  cancelContract,
  confirmDelivery,
  createCreditContract,
  dispatchGoods,
  fundEscrow,
  getContractState,
  raiseDispute,
  recordRepayment,
  settleContract,
} from "../services/contract";
import { getContractEvents } from "../services/events";
import { AppError, asErrorMessage } from "../utils/errors";

export const contractsRouter = Router();

contractsRouter.post("/create", async (req, res) => {
  try {
    const { merchantWalletId, supplierWalletId, amount, dispatchDeadlineHours } =
      req.body as {
        merchantWalletId?: string;
        supplierWalletId?: string;
        amount?: number;
        dispatchDeadlineHours?: number;
      };

    if (!merchantWalletId || !supplierWalletId) {
      throw new AppError("merchantWalletId and supplierWalletId are required", 400);
    }

    if (typeof amount !== "number" || amount <= 0) {
      throw new AppError("amount must be a positive number", 400);
    }

    if (
      typeof dispatchDeadlineHours !== "number" ||
      dispatchDeadlineHours <= 0
    ) {
      throw new AppError("dispatchDeadlineHours must be a positive number", 400);
    }

    const created = await createCreditContract({
      merchantWalletId,
      supplierWalletId,
      amount,
      dispatchDeadlineHours,
    });

    return res.status(201).json(created);
  } catch (error) {
    console.error("Error creating contract:", error);
    const statusCode = error instanceof AppError ? error.statusCode : 500;
    return res.status(statusCode).json({ error: asErrorMessage(error) });
  }
});

contractsRouter.post("/:id/fund", async (req, res) => {
  try {
    const { fromWalletId, amount } = req.body as {
      fromWalletId?: string;
      amount?: number;
    };

    if (!fromWalletId) {
      throw new AppError("fromWalletId is required", 400);
    }

    if (typeof amount !== "number" || amount <= 0) {
      throw new AppError("amount must be a positive number", 400);
    }

    const result = await fundEscrow(req.params.id, fromWalletId, amount);
    return res.json(result);
  } catch (error) {
    const statusCode = error instanceof AppError ? error.statusCode : 500;
    return res.status(statusCode).json({ error: asErrorMessage(error) });
  }
});

contractsRouter.post("/:id/dispatch", async (req, res) => {
  try {
    const { supplierWalletId } = req.body as { supplierWalletId?: string };

    if (!supplierWalletId) {
      throw new AppError("supplierWalletId is required", 400);
    }

    const result = await dispatchGoods(req.params.id, supplierWalletId);
    return res.json(result);
  } catch (error) {
    const statusCode = error instanceof AppError ? error.statusCode : 500;
    return res.status(statusCode).json({ error: asErrorMessage(error) });
  }
});

contractsRouter.post("/:id/deliver", async (req, res) => {
  try {
    const { merchantWalletId } = req.body as { merchantWalletId?: string };

    if (!merchantWalletId) {
      throw new AppError("merchantWalletId is required", 400);
    }

    const result = await confirmDelivery(req.params.id, merchantWalletId);
    return res.json(result);
  } catch (error) {
    const statusCode = error instanceof AppError ? error.statusCode : 500;
    return res.status(statusCode).json({ error: asErrorMessage(error) });
  }
});

contractsRouter.post("/:id/repay", async (req, res) => {
  try {
    const { amount } = req.body as { amount?: number };

    if (typeof amount !== "number" || amount <= 0) {
      throw new AppError("amount must be a positive number", 400);
    }

    const result = await recordRepayment(req.params.id, amount);
    return res.json(result);
  } catch (error) {
    const statusCode = error instanceof AppError ? error.statusCode : 500;
    return res.status(statusCode).json({ error: asErrorMessage(error) });
  }
});

contractsRouter.post("/:id/settle", async (req, res) => {
  try {
    const result = await settleContract(req.params.id);
    return res.json(result);
  } catch (error) {
    const statusCode = error instanceof AppError ? error.statusCode : 500;
    return res.status(statusCode).json({ error: asErrorMessage(error) });
  }
});

contractsRouter.post("/:id/dispute", async (req, res) => {
  try {
    const { reason, raisedBy } = req.body as {
      reason?: string;
      raisedBy?: string;
    };

    if (!reason) {
      throw new AppError("reason is required", 400);
    }

    if (!raisedBy) {
      throw new AppError("raisedBy is required", 400);
    }

    const result = await raiseDispute(req.params.id, reason, raisedBy);
    return res.json(result);
  } catch (error) {
    const statusCode = error instanceof AppError ? error.statusCode : 500;
    return res.status(statusCode).json({ error: asErrorMessage(error) });
  }
});

contractsRouter.post("/:id/cancel", async (req, res) => {
  try {
    const result = await cancelContract(req.params.id);
    return res.json(result);
  } catch (error) {
    const statusCode = error instanceof AppError ? error.statusCode : 500;
    return res.status(statusCode).json({ error: asErrorMessage(error) });
  }
});

contractsRouter.get("/:id/status", async (req, res) => {
  try {
    const state = await getContractState(req.params.id);
    console.log("Contract state:", state);
    return res.json({
      contractId: state.contractId,
      status: state.status,
      amount: state.amount,
      repaid: state.repaid,
      escrowBalance: state.escrowBalance,
      raw: state.raw,
    });
  } catch (error) {
    console.log(error)
    const statusCode = error instanceof AppError ? error.statusCode : 500;
    return res.status(statusCode).json({ error: asErrorMessage(error) });
  }
});

contractsRouter.get("/:id/events", async (req, res) => {
  try {
    const events = await getContractEvents(req.params.id);
    return res.json(events);
  } catch (error) {
    console.log("Contract events error:", error);
    const statusCode = error instanceof AppError ? error.statusCode : 500;
    return res.status(statusCode).json({ error: asErrorMessage(error) });
  }
});
