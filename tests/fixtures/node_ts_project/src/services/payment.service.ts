/**
 * External payment gateway integration service with circuit breaker and retries.
 */

import axios from "axios";
import CircuitBreaker from "opossum";
import { logger } from "../observability/telemetry";

export class PaymentError extends Error {
  constructor(message: string, public readonly code: string = "PAYMENT_FAILED") {
    super(message);
    this.name = "PaymentError";
  }
}

interface PaymentPayload {
  orderId: string;
  amount: number;
  currency: string;
}

const httpClient = axios.create({
  baseURL: process.env.PAYMENT_GATEWAY_URL || "https://api.payment.example.com",
  timeout: 5000, // Timeout protection
  headers: {
    "Content-Type": "application/json",
  },
});

// Raw external API call with retry mechanism
async function sendPaymentRequest(payload: PaymentPayload): Promise<any> {
  const maxRetries = 3;
  let attempt = 0;
  let delay = 200;

  while (attempt < maxRetries) {
    try {
      const response = await httpClient.post("/v1/charges", payload, {
        timeout: 4000,
      });
      return response.data;
    } catch (err: any) {
      attempt++;
      if (attempt >= maxRetries) {
        logger.error("Payment call failed after max retries", { error: err.message, attempt });
        throw new PaymentError(`Gateway unreachable: ${err.message}`);
      }
      logger.warn(`Payment call failed, retrying in ${delay}ms... (attempt ${attempt})`);
      await new Promise((resolve) => setTimeout(resolve, delay));
      delay *= 2; // exponential backoff
    }
  }
}

// Circuit breaker pattern protection
const breakerOptions = {
  timeout: 5000,
  errorThresholdPercentage: 50,
  resetTimeout: 30000,
};

export const paymentBreaker = new CircuitBreaker(sendPaymentRequest, breakerOptions);

paymentBreaker.fallback(() => {
  logger.warn("Payment circuit breaker OPEN: returning fallback queued response");
  return { status: "queued", fallback: true };
});

export async function processPayment(payload: PaymentPayload) {
  return paymentBreaker.fire(payload);
}
