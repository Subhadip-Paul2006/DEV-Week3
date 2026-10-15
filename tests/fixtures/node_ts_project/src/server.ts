/**
 * Main application entrypoint: Express server setup, middleware pipeline,
 * security headers, rate limiting, and health checks.
 */

import http from "http";
import express, { Request, Response, NextFunction } from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import { config, validateConfig } from "./config";
import { router } from "./routes/api";
import { logger, metricsRegistry, httpRequestCounter } from "./observability/telemetry";
import { checkDatabaseHealth } from "./db/prisma";
import { initWebSocketServer } from "./workers/queue";

// Validate environment on boot
validateConfig();

export const app = express();
const server = http.createServer(app);

// 1. Security Headers via Helmet
app.use(helmet());

// 2. CORS configuration with explicit origin
app.use(
  cors({
    origin: ["https://dashboard.example.com", "https://admin.example.com"],
    methods: ["GET", "POST", "PUT", "DELETE"],
    credentials: true,
  })
);

// 3. Body parsing
app.use(express.json());

// 4. Rate Limiting Protection
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per window
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: "Too many requests, please try again later." },
});
app.use("/api/", limiter);

// 5. Metrics collection middleware
app.use((req: Request, res: Response, next: NextFunction) => {
  res.on("finish", () => {
    httpRequestCounter.inc({
      method: req.method,
      route: req.route?.path || req.path,
      status_code: res.statusCode.toString(),
    });
  });
  next();
});

// 6. Health & Readiness endpoints
app.get("/health", (_req: Request, res: Response) => {
  res.status(200).json({ status: "healthy", timestamp: new Date().toISOString() });
});

app.get("/ready", async (_req: Request, res: Response) => {
  const dbHealthy = await checkDatabaseHealth();
  if (!dbHealthy) {
    return res.status(503).json({ status: "unhealthy", reason: "Database connection failed" });
  }
  return res.status(200).json({ status: "ready" });
});

// 7. Prometheus metrics endpoint
app.get("/metrics", async (_req: Request, res: Response) => {
  res.set("Content-Type", metricsRegistry.contentType);
  res.end(await metricsRegistry.metrics());
});

// 8. API Routes
app.use("/api", router);

// 9. Centralized Error Handling Middleware
app.use((err: Error, req: Request, res: Response, _next: NextFunction) => {
  logger.error("Unhandled error in request pipeline", {
    error: err.message,
    stack: err.stack,
    path: req.path,
  });
  res.status(500).json({ error: "Internal server error" });
});

// 10. Real-time WebSocket Server
initWebSocketServer(server);

// Start server listening
if (process.env.NODE_ENV !== "test") {
  server.listen(config.port, () => {
    logger.info(`Server running on port ${config.port}`);
  });
}
