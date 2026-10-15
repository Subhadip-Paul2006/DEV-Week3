/**
 * React Dashboard component demonstrating React / TSX heuristics and caching.
 */

import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

interface Order {
  id: string;
  amount: number;
  status: string;
}

async function fetchOrders(): Promise<Order[]> {
  const response = await fetch("/api/orders");
  if (!response.ok) {
    throw new Error("Failed to load orders");
  }
  return response.json();
}

export const Dashboard: React.FC = () => {
  const [selectedStatus, setSelectedStatus] = useState<string>("all");

  const { data: orders, isLoading, error } = useQuery({
    queryKey: ["orders", selectedStatus],
    queryFn: fetchOrders,
    staleTime: 60 * 1000, // 1 minute client cache
  });

  return (
    <main role="main" aria-label="Order Management Dashboard" className="dashboard-container">
      <header>
        <h1>System Architecture Dashboard</h1>
      </header>

      <section role="region" aria-label="Order Statistics" className="order-stats">
        {isLoading && <p role="status">Loading order data...</p>}
        {error && <p role="alert">Error loading orders: {(error as Error).message}</p>}

        {orders && (
          <ul aria-label="Orders List">
            {orders.map((order) => (
              <li key={order.id} aria-label={`Order ${order.id}`}>
                <span>{order.id}</span> - <span>${order.amount.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
};
