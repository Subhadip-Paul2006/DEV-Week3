package com.example.app;

import org.springframework.stereotype.Service;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.retry.annotation.Retryable;
import org.springframework.retry.annotation.Recover;
import org.springframework.retry.annotation.Backoff;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Service
public class OrderService {

    private static final Logger logger = LoggerFactory.getLogger(OrderService.class);
    private final OrderRepository repository;

    public OrderService(OrderRepository repository) {
        this.repository = repository;
    }

    @Cacheable(value = "orders", key = "#id")
    @CircuitBreaker(name = "orderService", fallbackMethod = "fallbackOrder")
    public Order findOrder(String id) {
        logger.info("Looking up order {}", id);
        return repository.findById(id).orElse(null);
    }

    @Retryable(maxAttempts = 3, backoff = @Backoff(delay = 1000, multiplier = 2))
    public Order processOrder(Order order) {
        logger.info("Processing order for amount {}", order.getAmount());
        return repository.save(order);
    }

    @Recover
    public Order recover(Exception e, Order order) {
        logger.error("Failed to process order after retries", e);
        return null;
    }

    public Order fallbackOrder(String id, Throwable t) {
        logger.warn("Circuit breaker fallback for order {}", id);
        return new Order(id, 0.0, "FALLBACK");
    }
}
