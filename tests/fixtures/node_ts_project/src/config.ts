/**
 * Application environment configuration and secrets loader.
 */

import dotenv from "dotenv";
import { z } from "zod";

// Load environment variables from .env
dotenv.config();

const envSchema = z.object({
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  PORT: z.string().transform(Number).default("3000"),
  DATABASE_URL: z.string().min(1, "DATABASE_URL is required"),
  REDIS_URL: z.string().default("redis://localhost:6379"),
  JWT_SECRET: z.string().min(32, "JWT_SECRET must be at least 32 characters"),
  PAYMENT_GATEWAY_URL: z.string().url(),
  LOG_LEVEL: z.enum(["error", "warn", "info", "debug"]).default("info"),
});

export const config = {
  env: process.env.NODE_ENV || "development",
  port: parseInt(process.env.PORT || "3000", 10),
  databaseUrl: process.env.DATABASE_URL || "",
  redisUrl: process.env.REDIS_URL || "redis://localhost:6379",
  jwtSecret: process.env.JWT_SECRET || "",
  paymentGatewayUrl: process.env.PAYMENT_GATEWAY_URL || "https://api.payment.example.com",
  logLevel: process.env.LOG_LEVEL || "info",
};

export function validateConfig() {
  const parsed = envSchema.safeParse(process.env);
  if (!parsed.success) {
    console.error("Configuration validation error:", parsed.error.format());
    throw new Error("Invalid configuration");
  }
  return parsed.data;
}
