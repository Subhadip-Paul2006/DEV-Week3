/**
 * Observability: Structured logging, Prometheus metrics, and OpenTelemetry tracing.
 */

import winston from "winston";
import { Counter, Histogram, Registry } from "prom-client";

// Structured Logging via Winston
export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || "info",
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: { service: "order-service" },
  transports: [
    new winston.transports.Console(),
  ],
});

// Prometheus Metrics Registry
export const metricsRegistry = new Registry();

export const httpRequestCounter = new Counter({
  name: "http_requests_total",
  help: "Total number of HTTP requests processed",
  labelNames: ["method", "route", "status_code"],
  registers: [metricsRegistry],
});

export const httpDurationHistogram = new Histogram({
  name: "http_request_duration_seconds",
  help: "HTTP request latency distributions in seconds",
  labelNames: ["method", "route", "status_code"],
  buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
  registers: [metricsRegistry],
});

// Tracing tracer stub for distributed traces
export function getTracer(name: string) {
  return {
    startSpan: (spanName: string) => ({
      setAttribute: (_k: string, _v: string) => {},
      end: () => {},
    }),
  };
}
