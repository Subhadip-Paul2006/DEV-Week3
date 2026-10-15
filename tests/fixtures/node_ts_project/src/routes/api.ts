/**
 * API Routes: Order handling, authentication middleware, validation, and pagination.
 */

import { Router, Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import bcrypt from "bcrypt";
import { z } from "zod";
import { prisma } from "../db/prisma";
import { cache } from "../cache/redis";
import { orderQueue } from "../workers/queue";
import { logger } from "../observability/telemetry";

export const router = Router();

// Zod schema for order validation
const createOrderSchema = z.object({
  customerId: z.string().uuid(),
  amount: z.number().positive(),
  items: z.array(z.string()).min(1),
});

// Authentication middleware using JWT
export function authMiddleware(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return res.status(401).json({ error: "Missing or invalid authorization token" });
  }

  const token = authHeader.split(" ")[1];
  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET || "default-secret");
    (req as any).user = payload;
    next();
  } catch (err) {
    return res.status(403).json({ error: "Invalid token" });
  }
}

// Role-based authorization guard
export function checkRole(role: string) {
  return (req: Request, res: Response, next: NextFunction) => {
    const user = (req as any).user;
    if (!user || user.role !== role) {
      return res.status(403).json({ error: "Insufficient permissions" });
    }
    next();
  };
}

// Order listing with pagination support
router.get("/orders", authMiddleware, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const page = parseInt(req.query.page as string || "1", 10);
    const limit = parseInt(req.query.limit as string || "20", 10);
    const offset = (page - 1) * limit;

    const cacheKey = `orders:page:${page}:limit:${limit}`;
    const cached = await cache.get(cacheKey);
    if (cached) {
      return res.json({ source: "cache", data: cached });
    }

    const orders = await prisma.order.findMany({
      skip: offset,
      take: limit,
      orderBy: { createdAt: "desc" },
    });

    await cache.set(cacheKey, orders, 60);
    return res.json({ source: "database", page, limit, data: orders });
  } catch (err) {
    next(err);
  }
});

// Create order endpoint with validation and queueing
router.post("/orders", authMiddleware, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const parsed = createOrderSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: "Validation failed", details: parsed.error.issues });
    }

    const job = await orderQueue.add("process-order", parsed.data);
    logger.info("Order enqueued successfully", { jobId: job.id });

    return res.status(202).json({ message: "Order accepted for processing", jobId: job.id });
  } catch (err) {
    next(err);
  }
});
