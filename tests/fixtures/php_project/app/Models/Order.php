<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\DB;

class Order extends Model
{
    protected $table = 'orders';
    protected $fillable = ['user_id', 'total_amount', 'status'];

    public static function createOrder(array $attributes)
    {
        return DB::transaction(function () use ($attributes) {
            $order = static::create($attributes);
            DB::table('order_logs')->insert([
                'order_id' => $order->id,
                'action' => 'created',
                'created_at' => now(),
            ]);
            return $order;
        });
    }
}
