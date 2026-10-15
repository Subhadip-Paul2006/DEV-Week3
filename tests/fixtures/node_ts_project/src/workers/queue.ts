/**
 * Background async workers and real-time WebSocket notifications.
 */

import { Queue, Worker, QueueEvents } from "bullmq";
import { WebSocketServer, WebSocket } from "ws";
import { logger } from "../observability/telemetry";

const connection = {
  host: process.env.REDIS_HOST || "localhost",
  port: parseInt(process.env.REDIS_PORT || "6379", 10),
};

// BullMQ message broker queue with dead-letter queue setup
export const orderQueue = new Queue("orders", { connection });
export const deadLetterQueue = new Queue("orders-dlq", { connection });

export const orderWorker = new Worker(
  "orders",
  async (job) => {
    logger.info("Processing order background job", { jobId: job.id, data: job.data });
    // Process async order logic
    return { success: true };
  },
  {
    connection,
    concurrency: 5,
  }
);

orderWorker.on("failed", async (job, err) => {
  logger.error("Job failed permanently, moving to DLQ", { jobId: job?.id, error: err.message });
  if (job) {
    await deadLetterQueue.add("failed-order", { originalJob: job.data, reason: err.message });
  }
});

// WebSocket Server for real-time streaming notifications
export function initWebSocketServer(server: any) {
  const wss = new WebSocketServer({ server, path: "/ws/notifications" });

  wss.on("connection", (ws: WebSocket) => {
    logger.info("New WebSocket client connected");

    ws.on("message", (message: string) => {
      logger.debug("Received WebSocket message", { message: message.toString() });
    });

    ws.on("close", () => {
      logger.info("WebSocket client disconnected");
    });
  });

  return wss;
}
