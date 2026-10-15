<?php

namespace App\Controllers;

use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Auth;
use App\Models\Order;
use App\Jobs\ProcessPayment;

class OrderController extends Controller
{
    public function show($id)
    {
        Log::info("Fetching order: " . $id);

        $order = Cache::remember('order:' . $id, 600, function () use ($id) {
            return Order::find($id);
        });

        if (!$order) {
            return response()->json(['error' => 'Not Found'], 404);
        }

        return response()->json($order);
    }

    public function store($request)
    {
        $userId = Auth::id();
        Log::info("Creating order for user: " . $userId);

        $order = Order::createOrder($request->all());

        // Dispatch asynchronous background job to queue
        dispatch(new ProcessPayment($order->id));

        return response()->json($order, 201);
    }
}
