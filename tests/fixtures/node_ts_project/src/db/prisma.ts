/**
 * Database access layer using Prisma ORM with connection pooling.
 */

import { PrismaClient } from "@prisma/client";
import { logger } from "../observability/telemetry";

// Initialize Prisma client with connection pooling
export const prisma = new PrismaClient({
  datasources: {
    db: {
      url: process.env.DATABASE_URL,
    },
  },
  log: [
    { emit: "event", level: "query" },
    { emit: "event", level: "error" },
  ],
});

// Configure connection pool settings
export const poolConfig = {
  max: 20,
  min: 5,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
};

export async function checkDatabaseHealth(): Promise<boolean> {
  try {
    await prisma.$queryRaw`SELECT 1`;
    return true;
  } catch (error) {
    logger.error("Database health check failed", { error });
    return false;
  }
}
