"""Business services: caching, resilience, messaging, auth, and external calls."""

from __future__ import annotations

import html
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
import jwt
import pika
import pybreaker
import redis
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
from .observability import logger, tracer

# 1. Caching with Redis
redis_client = redis.from_url(settings.redis.url, decode_responses=True)


def cache_get(key: str) -> Optional[Dict[str, Any]]:
    """Retrieve serialized JSON item from Redis cache."""
    val = redis_client.get(key)
    if val:
        return json.loads(val)
    return None


def cache_set(key: str, data: Dict[str, Any], ttl: int = 300) -> None:
    """Store serialized JSON item in Redis cache with TTL."""
    redis_client.set(key, json.dumps(data), ex=ttl)


# 2. Resilience: Circuit Breaker
payment_circuit_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
    name="payment_gateway_breaker",
)


# 3. Resilience: Retries with Exponential Backoff
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _send_payment_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute raw HTTP request to payment processor with timeout."""
    with httpx.Client(timeout=10.0) as client:
        resp = client.post("https://payment.provider.internal/v1/charge", json=payload)
        resp.raise_for_status()
        return resp.json()


def process_payment(order_id: int, amount: float) -> Dict[str, Any]:
    """Process a customer payment through circuit breaker protected call."""
    with tracer.start_as_current_span("process_payment_call"):
        logger.info(f"Initiating payment for order {order_id} of {amount}")
        payload = {"order_id": order_id, "amount": amount}
        # Wrap retry logic inside circuit breaker
        return payment_circuit_breaker.call(_send_payment_request, payload)


# 4. Streaming & Messaging: RabbitMQ Message Broker
def publish_order_event(order_id: int, event_type: str) -> None:
    """Publish an order domain event to RabbitMQ message broker."""
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        channel = connection.channel()
        channel.queue_declare(queue="order_events", durable=True)
        message_body = json.dumps({"order_id": order_id, "event": event_type, "timestamp": datetime.utcnow().isoformat()})
        channel.basic_publish(
            exchange="",
            routing_key="order_events",
            body=message_body,
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()
    except Exception as exc:
        logger.error(f"Failed to publish message broker event: {exc}")


# 5. Security & Authentication: JWT Tokens
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.security.token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.security.jwt_secret_key, algorithm=settings.security.jwt_algorithm)


def verify_access_token(token: str) -> Optional[dict]:
    """Verify and decode signed JWT token."""
    try:
        payload = jwt.decode(token, settings.security.jwt_secret_key, algorithms=[settings.security.jwt_algorithm])
        return payload
    except jwt.PyJWTError:
        return None


# 6. Authorization: Role-based Guard
def check_user_role(user_data: dict, required_role: str) -> bool:
    """Validate user has role-based access permission."""
    roles = user_data.get("roles", [])
    return required_role in roles or "admin" in roles


# 7. Input Sanitization
def sanitize_comment(raw_text: str) -> str:
    """Sanitize user provided comment to prevent cross-site scripting."""
    return html.escape(raw_text.strip())
