<?php

namespace App\Jobs;

use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Support\Facades\Log;

class ProcessPayment implements ShouldQueue
{
    public $orderId;

    public function __construct($orderId)
    {
        $this->orderId = $orderId;
    }

    public function handle()
    {
        Log::info("Processing payment asynchronously for order " . $this->orderId);
        \Illuminate\Support\Facades\Http::timeout(5)->post("https://payment.gateway/charge", [
            'order_id' => $this->orderId,
        ]);
    }
}

