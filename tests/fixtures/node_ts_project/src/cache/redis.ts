/**
 * Caching layer using Redis client with TTL and invalidation strategies.
 */

import Redis from "ioredis";
import { logger } from "../observability/telemetry";

const redisClient = new Redis(process.env.REDIS_URL || "redis://localhost:6379", {
  maxRetriesPerRequest: 3,
  enableReadyCheck: true,
  lazyConnect: true,
});

redisClient.on("error", (err) => {
  logger.error("Redis connection error", { error: err.message });
});

export class CacheService {
  private client: Redis;

  constructor(client: Redis = redisClient) {
    this.client = client;
  }

  async get<T>(key: string): Promise<T | null> {
    try {
      const data = await this.client.get(key);
      if (!data) return null;
      return JSON.parse(data) as T;
    } catch (err) {
      logger.warn("Cache read error", { key, error: (err as Error).message });
      return null;
    }
  }

  async set<T>(key: string, value: T, ttlSeconds: number = 300): Promise<void> {
    try {
      const serialized = JSON.stringify(value);
      await this.client.set(key, serialized, "EX", ttlSeconds);
    } catch (err) {
      logger.warn("Cache write error", { key, error: (err as Error).message });
    }
  }

  async invalidate(pattern: string): Promise<void> {
    try {
      const keys = await this.client.keys(pattern);
      if (keys.length > 0) {
        await this.client.del(...keys);
      }
    } catch (err) {
      logger.warn("Cache invalidation error", { pattern, error: (err as Error).message });
    }
  }
}

export const cache = new CacheService();
