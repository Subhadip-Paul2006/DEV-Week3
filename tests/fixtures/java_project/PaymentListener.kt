package com.example.app

import org.springframework.kafka.annotation.KafkaListener
import org.springframework.stereotype.Component
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Component
class PaymentListener {

    @KafkaListener(topics = ["payments"], groupId = "payment-group")
    suspend fun onPaymentReceived(message: String) = withContext(Dispatchers.IO) {
        println("Processing payment in coroutine: $message")
    }

    fun initWeb3Rpc() {
        val client = org.web3j.protocol.Web3j.build(org.web3j.protocol.http.HttpService("https://rpc.example.com"))
    }
}

