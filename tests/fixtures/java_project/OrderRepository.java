package com.example.app;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "orders")
class Order {
    @Id
    private String id;
    private Double amount;
    private String status;

    public Order() {}

    public Order(String id, Double amount, String status) {
        this.id = id;
        this.amount = amount;
        this.status = status;
    }

    public String getId() { return id; }
    public Double getAmount() { return amount; }
    public String getStatus() { return status; }
}

@Repository
public interface OrderRepository extends JpaRepository<Order, String> {
}
