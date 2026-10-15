<?php

use Illuminate\Support\Facades\Route;
use App\Controllers\OrderController;

Route::get('/health', function () {
    return response()->json(['status' => 'ok']);
});

Route::get('/healthz', function () {
    return response()->json(['status' => 'ok']);
});

Route::middleware('throttle:60,1')->group(function () {
    Route::get('/api/orders/{id}', [OrderController::class, 'show']);
    Route::post('/api/orders', [OrderController::class, 'store']);
});
