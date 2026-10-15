---
id: foundation.message-queues
category: foundation
owning_agent: F-07
maturity: stable
languages:
- any
tags:
- async
- pub-sub
- event-driven
- dead-letter
related:
- foundation.fault-tolerance
- foundation.idempotency
- foundation.circuit-breaker
domain: core
---

# Message Queues

## 1. Overview

A message queue is an asynchronous, durable communication channel that decouples producers from consumers by buffering messages in a broker between them. Producers publish events without knowing who (if anyone) will process them, and consumers pull work at their own pace, surviving network failures, slow downs, and restarts. Message queues are the backbone of event-driven architectures: they convert synchronous request/response calls (which fail loudly and immediately) into fire-and-forget asynchronous work (which can be retried, reordered, dead-lettered, or replayed hours later). They exist because tightly coupled synchronous calls cannot scale to bursty workloads, cannot survive downstream outages, and cannot fan out work to many independent workers.

## 2. Core Principles

- **Decoupling is the goal, not the side effect.** If a producer knows the consumer's identity, type, or number, the queue has not done its job. Use topic-based or content-based routing and accept that consumers can come and go without producer changes.
- **At-least-once delivery is the default for almost every broker** (RabbitMQ, Kafka with acks, SQS standard, Pub/Sub). Consumers must be idempotent or duplicates will cause data corruption. The broker guarantees "you'll see it again"; it does NOT guarantee "you'll see it exactly once."
- **Backpressure is a feature, not a failure.** When consumers slow down, queues grow. A healthy system observes queue depth and sheds load early (e.g., reject publishes, return 503 to upstream) rather than letting memory fill until the broker OOMs.
- **Messages must carry enough context to be processed without out-of-band lookup.** Including a `correlation_id`, `traceparent`, schema version, and tenant ID in the envelope is not optional — it is the only way to debug a fire-and-forget pipeline two days later.
- **Ordering is only preserved within a partition/key.** A queue with 32 partitions gives 32 independent orderings. Engineers who assume global ordering across a multi-partition topic will see subtle bugs.
- **Durability is a configuration choice, not a guarantee.** `acks=0` in Kafka, `autoAck=true` in RabbitMQ, and SQS standard (non-FIFO) all sacrifice durability for throughput or latency. The default is not always the safest.
- **The queue is part of the API contract.** Removing a queue, renaming a topic, or changing a schema is a breaking change that requires the same care as a REST API version bump.

## 3. Sub-Concepts

### 3.1 Brokers and Their Delivery Semantics

**Definition:** The broker is the server that durably stores messages until consumers acknowledge them. Three families dominate: AMQP brokers (RabbitMQ), log-based brokers (Apache Kafka, Redpanda), and cloud-native queues (AWS SQS/SNS, Google Pub/Sub, Azure Service Bus).

**Why it matters:** The broker choice dictates the delivery guarantee, ordering model, max throughput, and operational footprint. Picking Kafka for "easy pub/sub" or RabbitMQ for "high-throughput event sourcing" both create pain.

**Implementation patterns:**
- **RabbitMQ** — exchanges (`direct`, `topic`, `fanout`, `headers`), bindings, queues, message acknowledgments, mandatory publishing. Routing is content- or header-based. Excellent for task distribution, RPC-style patterns, low-latency.
- **Kafka** — topics, partitions, consumer groups, offsets. Routing is partition-key based. Excellent for event sourcing, stream processing, replay-from-offset. Durable by default (`acks=all`, `min.insync.replicas=2`).
- **SQS** — managed queues, no infrastructure, visibility timeout, dead-letter queues. Excellent for AWS-native workloads, batch operations, and "fire and forget with retries" semantics.
- **Pub/Sub** — managed topics with push or pull subscriptions, message ordering keys, exactly-once disabled by default.

**Common mistakes:** Treating Kafka like RabbitMQ (expecting per-message acknowledgments), treating RabbitMQ like Kafka (expecting to replay from offset 5 days ago), assuming SQS messages are FIFO without enabling FIFO queues.

**Scanner signals:** Look for broker client imports (`@aws-sdk/client-sqs`, `google-cloud/pubsub`, `amqplib`, `kafkajs`, `confluent-kafka`, `boto3` + SQS calls), broker connection strings (`amqp://`, `kafka://`, `pubsub://`), and topic/queue declarations.

### 3.2 Producer Patterns (Publish Confirmations, Batching, Routing Keys)

**Definition:** A producer is any code that publishes messages to a broker. It must decide how to confirm success, batch for throughput, choose routing keys, and handle publish failures.

**Why it matters:** A producer that loses messages silently (no publisher confirms) is worse than no queue at all — it gives false confidence. A producer that blocks on every publish caps throughput at network RTT.

**Implementation patterns:**
```python
# ❌ WRONG — fire and forget, no confirmation
import pika
conn = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
ch = conn.channel()
ch.basic_publish(exchange='orders', routing_key='new', body=json.dumps(order))
# If the broker is down or the message is unroutable, no one knows.

# ✅ CORRECT — publisher confirms + mandatory flag
ch.confirm_delivery()
try:
    ch.basic_publish(
        exchange='orders',
        routing_key='new',
        body=json.dumps(order),
        mandatory=True,        # broker returns unroutable messages
        properties=pika.BasicProperties(
            delivery_mode=2,   # persistent
            content_type='application/json',
            message_id=str(uuid.uuid4()),
            correlation_id=correlation_id,
            timestamp=int(time.time()),
        ),
    )
except pika.exceptions.UnroutableError:
    metrics.increment('producer.unroutable')
    raise
except pika.exceptions.NackError:
    metrics.increment('producer.nack')
    # retry with backoff or write to dead-letter store
```
```typescript
// ✅ CORRECT — KafkaJS with idempotent producer
import { Kafka, Partitioners, CompressionTypes } from 'kafkajs';

const kafka = new Kafka({ clientId: 'orders-svc', brokers: ['kafka:9092'] });
const producer = kafka.producer({
  idempotent: true,
  maxInFlightRequests: 5,
  transactionTimeout: 30000,
  createPartitioner: Partitioners.DefaultPartitioner,
});

await producer.connect();
await producer.send({
  topic: 'orders.created',
  acks: -1,                    // wait for all in-sync replicas
  compression: CompressionTypes.Gzip,
  messages: [{
    key: order.customerId,     // ensures per-customer ordering
    value: JSON.stringify(order),
    headers: { 'correlation-id': correlationId, 'schema-version': '2' },
  }],
});
```
```go
// ✅ CORRECT — AWS SQS with batching and message attributes
sqsClient := sqs.NewFromConfig(cfg)

_, err := sqsClient.SendMessageBatch(ctx, &sqs.SendMessageBatchInput{
    QueueUrl: aws.String(queueURL),
    Entries: []types.SendMessageBatchRequestEntry{
        {
            Id:          aws.String("1"),
            MessageBody: aws.String(string(orderJSON)),
            MessageAttributes: map[string]types.MessageAttributeValue{
                "event-type":   {StringValue: aws.String("order.created"), DataType: aws.String("String")},
                "tenant-id":    {StringValue: aws.String(order.TenantID), DataType: aws.String("String")},
                "traceparent":  {StringValue: aws.String(traceparent), DataType: aws.String("String")},
            },
            MessageDeduplicationId: aws.String(order.EventID), // FIFO only
            MessageGroupId:         aws.String(order.CustomerID),
        },
    },
})
```

**Common mistakes:** Using `acks=0` or `acks=1` on Kafka (loses messages on broker failure); not enabling publisher confirms on RabbitMQ; setting `autoCreateTopics=true` in production; publishing inside a database transaction without an outbox pattern (transaction commits but publish fails = lost event).

**Scanner signals:** Look for `acks=` configuration, `mandatory` flag on publishes, `confirmSelect`/`confirm_delivery` calls, presence of an outbox table or `OutboxProcessor` class.

### 3.3 Consumer Patterns (Acknowledgment, Prefetch, Concurrency)

**Definition:** A consumer is any code that subscribes to a queue/topic and processes messages. It controls the rate of consumption via prefetch, commits offsets/acks after successful processing, and handles failures.

**Why it matters:** A consumer that `auto-acks` before processing will lose messages on crash. A consumer with `prefetch=1` underutilizes workers. A consumer that blocks forever on a downstream service will pin the queue.

**Implementation patterns:**
```python
# ❌ WRONG — auto-ack, unbounded processing
ch.basic_consume(queue='orders', on_message_callback=process_order, auto_ack=True)
# Crash mid-process = message lost forever.

# ✅ CORRECT — manual ack after success, nack to requeue on failure
def callback(ch, method, properties, body):
    try:
        process_order(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except RetryableError:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        # False → message goes to DLX (dead-letter exchange)
    except Exception:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

ch.basic_qos(prefetch_count=10)   # bound in-flight messages
ch.basic_consume(queue='orders', on_message_callback=callback, auto_ack=False)
```
```typescript
// ✅ CORRECT — KafkaJS eachMessage with manual offset commit
const consumer = kafka.consumer({
  groupId: 'order-fulfillment',
  maxBytesPerPartition: 1_048_576,
  sessionTimeout: 30000,
  heartbeatInterval: 3000,
});

await consumer.connect();
await consumer.subscribe({ topic: 'orders.created', fromBeginning: false });
await consumer.run({
  autoCommit: false,
  eachMessage: async ({ topic, partition, message, heartbeat }) => {
    try {
      await processOrder(message);
      await consumer.commitOffsets([{
        topic, partition, offset: (BigInt(message.offset) + 1n).toString(),
      }]);
      await heartbeat();
    } catch (err) {
      // do NOT commit; Kafka will redeliver
      throw err;
    }
  },
});
```

**Common mistakes:** Setting `prefetchCount` to 0 (unbounded — kills the broker), processing inside the broker thread (blocks all consumers), not handling `connection.blocked` events when the broker is in flow control.

**Scanner signals:** Look for `prefetch_count`/`max.in.flight`, `autoCommit: false`/`auto_ack=False`, presence of `try/except` around message handlers, `consumer.commitOffsets` / `ch.basic_ack` calls.

### 3.4 Delivery Guarantees (At-Most-Once, At-Least-Once, Exactly-Once)

**Definition:** The contract between broker and consumer about what happens when messages are duplicated, lost, or reordered.

- **At-most-once:** messages may be lost but never duplicated. Achieved by acking before processing. Almost never acceptable.
- **At-least-once:** messages may be duplicated but never lost. The default for every mainstream broker. Consumers must dedupe.
- **Exactly-once:** messages processed exactly one time with no side effects on retries. Requires cooperation between producer (idempotent producer ID + sequence numbers), broker (transactions), and consumer (idempotent processing keyed by event ID).

**Why it matters:** Engineers say "exactly-once" when they mean "at-least-once with idempotent consumer." The Kafka transactional API gives exactly-once **across the broker**, but the downstream database write is still at-least-once unless the consumer deduplicates.

**Implementation patterns:**
- At-least-once + idempotent consumer: every consumer keeps a dedup store (Redis SETNX, DynamoDB conditional write, Postgres unique index on `event_id`) keyed by event ID.
- Kafka exactly-once: use `transactional.id`, `enable.idempotence=true`, and `sendOffsetsToTransaction` to commit consumer offsets and produced messages in one atomic transaction.
- SQS FIFO + deduplication: enabled per-queue with a 5-minute window.

**Scanner signals:** Look for `transactional.id` in Kafka configs, `MessageDeduplicationId` in SQS code, unique constraint on `event_id` columns in consumer databases, presence of a `processed_events` table.

### 3.5 Ordering Guarantees

**Definition:** Order in which messages are delivered to consumers. Single-partition queues (RabbitMQ default, SQS FIFO) preserve FIFO. Multi-partition topics (Kafka, Pub/Sub) preserve ordering only within a partition, which is determined by the partitioning key.

**Why it matters:** "Order created before order paid" is a meaningful invariant. If `paid` lands on a different partition from `created` and is processed first, the consumer sees a payment for an order that doesn't exist.

**Implementation patterns:**
- Kafka: choose a partitioning key that defines the ordering boundary (e.g., `order_id`). All events for one order go to one partition.
- RabbitMQ: use a single queue per ordering domain (e.g., one queue per `order_id` is impractical — use a consistent-hash exchange).
- SQS FIFO: use a `MessageGroupId` to preserve ordering per group.

**Scanner signals:** Look for partition key argument on publish, `MessageGroupId` in SQS code, consistent-hash exchange types.

### 3.6 Dead-Letter Queues (DLQ) and Poison-Pill Handling

**Definition:** A dead-letter queue is a secondary queue where messages land after they fail processing too many times, expire, or are explicitly rejected. It isolates "broken" messages from the main queue so a single poison pill does not block all subsequent work.

**Why it matters:** Without a DLQ, a malformed message will be redelivered forever, blocking its partition (RabbitMQ) or spinning the consumer (Kafka). With a DLQ, the broken message is quarantined for human inspection and the main flow continues.

**Implementation patterns:**
```python
# RabbitMQ — declare DLX on the main queue
ch.queue_declare(
    queue='orders',
    durable=True,
    arguments={
        'x-dead-letter-exchange': 'orders.dlx',
        'x-dead-letter-routing-key': 'dead',
        'x-message-ttl': 3600000,  # 1 hour; expired messages go to DLX
        'x-max-length': 100000,
    },
)

ch.queue_declare(queue='orders.dead', durable=True)
ch.queue_bind(queue='orders.dead', exchange='orders.dlx', routing_key='dead')
```
```typescript
// Kafka — non-blocking retry topic pattern (no native DLQ)
await consumer.run({
  eachMessage: async ({ message }) => {
    try {
      await processOrder(message);
    } catch (err) {
      const retryCount = (message.headers['retry-count'] ?? 0) + 1;
      if (retryCount >= 5) {
        await producer.send({
          topic: 'orders.dead',
          messages: [{
            key: message.key,
            value: message.value,
            headers: { ...message.headers, 'retry-count': retryCount, 'error': err.message },
          }],
        });
      } else {
        await producer.send({
          topic: 'orders.retry',
          messages: [{
            key: message.key,
            value: message.value,
            headers: { ...message.headers, 'retry-count': retryCount },
          }],
        });
      }
    }
  },
});
```

**Common mistakes:** DLQ with no TTL → infinite growth → disk full. DLQ with no monitoring → "we lost data" discovered months later. Requeueing without a retry counter → poison pill loops forever.

**Scanner signals:** Look for `x-dead-letter-exchange` queue arguments, DLQ topic/queue names (`*.dead`, `*.dlq`, `*_dlq`), retry-count headers, retry topic producers.

### 3.7 Schema Evolution and Message Contracts

**Definition:** The shape of the message payload over time. Messages are API; if you change them without versioning, you break consumers deployed on older code.

**Why it matters:** Producer is on version 2 (new field `discount_cents`); consumer is on version 1 (does not know to ignore unknown fields). If the serialization format is strict (Protobuf with `reject_unknown_fields`, Avro without `defaultValue`), consumers crash.

**Implementation patterns:**
- Always include `schema-version` in headers or envelope.
- Use a schema registry (Confluent Schema Registry, Apicurio, AWS Glue Schema Registry) for Avro/Protobuf/JSON-Schema.
- Follow the compatibility rules: backward-compatible (new schema can read old data) is the safe default; forward-compatible (old schema can read new data) requires default values everywhere.
- For JSON: ignore unknown fields, use default values for missing fields.

**Scanner signals:** Look for `schema-version` header, schema registry URL config (`schema.registry.url`), Protobuf-generated descriptor files (`.proto`).

### 3.8 Observability

**Definition:** Metrics, logs, and traces that surface queue health to operators.

**Key metrics:**
- **Producer-side:** publish rate, publish error rate (nacks, unroutable, connection failures), publish latency p50/p95/p99.
- **Broker-side:** queue depth (number of ready messages), oldest message age, in-flight count, consumer lag (Kafka), connection count, channel count (RabbitMQ).
- **Consumer-side:** consume rate, processing duration, error rate, redelivery rate, DLQ rate.

**Alert thresholds:**
- Queue depth > 100k for 5 minutes → page.
- Oldest message age > 5 minutes → warn; > 30 minutes → page.
- Consumer lag (Kafka) > 10k messages or > 60 seconds behind → warn.
- DLQ depth growing > 0/min → page (data loss is occurring).
- Publish error rate > 1% → warn; > 5% → page.

**Scanner signals:** Look for Prometheus exporters (`rabbitmq_exporter`, `kafka_exporter`, `cloudwatch` integration), OpenTelemetry instrumentation on publish/consume calls, structured logs containing `correlation_id`.

### 3.9 Failure Modes

- **Broker outage:** producers and consumers disconnect; messages in flight are at risk (depending on durability config). Consumers must reconnect with exponential backoff. Producers must buffer locally or fail-fast.
- **Slow consumer:** queue grows; broker eventually applies flow control (RabbitMQ `connection.blocked`) or rejects produce (Kafka with `max.block.ms`). Health checks should report degraded.
- **Poison pill:** malformed message redelivered forever. Mitigated by DLQ + max retries.
- **Schema drift:** new field in payload crashes old consumer. Mitigated by schema registry + ignore-unknown-fields.
- **Clock skew:** if consumers rely on timestamps for ordering or TTL, NTP drift causes subtle bugs. Always rely on broker-assigned timestamps or offsets.
- **Cascading failures:** consumer A is down, blocking the queue; consumer B is also slow because the broker is in flow control. Mitigated by bounded queue + max-retries + circuit breaker on downstream calls.

### 3.10 Performance Characteristics

| Broker | Typical Throughput | Typical p99 Publish Latency | Max Message Size | Ordering |
|---|---|---|---|---|
| RabbitMQ | 10k–100k msg/s per node | 1–5 ms | 128 MB (configurable) | Per-queue FIFO |
| Kafka | 1M+ msg/s per cluster | 5–20 ms (acks=all) | 1 MB default, configurable | Per-partition |
| SQS Standard | Virtually unlimited | 10–100 ms | 256 KB | Best-effort |
| SQS FIFO | 300 msg/s without batching, 3000 with | 10–100 ms | 256 KB | Per-group FIFO |
| Pub/Sub | Millions/sec aggregate | 50–200 ms | 10 MB | Per-ordering-key |

Tuning levers: batch size, linger.ms, compression (Kafka), prefetch count, channel pool size, connection pool, producer thread count, broker-side partition count, consumer parallelism.

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Import of broker client library | All | regex: `import.*(?:pika\|amqplib\|aio-pika\|stomp\|kafkajs\|@confluentinc\|@aws-sdk/client-sqs\|google-cloud/pubsub\|boto3)` | High |
| Kafka topic name in config | All | regex: `(?:topic\|queue):\s*['"][a-zA-Z0-9._-]+['"]` | High |
| RabbitMQ exchange/queue declaration | Python, Go | regex: `queue_declare\|exchange_declare\|QueueDeclare\|ExchangeDeclare` | High |
| Kafka consumer group declaration | All | regex: `groupId:\s*['"]\|group_id\s*=\|consumer\.Subscribe\|Subscribe\(` | High |
| Producer instantiated with acks config | All | regex: `acks\s*[:=]\s*-?1\|all\|0` | High |
| Publisher confirms enabled | All | regex: `confirm_delivery\|confirmSelect\|ConfirmPublish` | High |
| Dead-letter queue argument | All | regex: `x-dead-letter-exchange\|deadLetterQueue\|DLQ\|dead-letter` | High |
| Message handler with ack | All | regex: `basic_ack\|basic_nack\|commitOffsets\|message\.ack\(\)` | High |
| Manual ack (auto_ack=False / autoCommit=False) | All | regex: `auto_ack\s*=\s*False\|autoCommit\s*:\s*false\|autoAck\s*[:=]\s*false` | High |
| Schema version in headers | All | regex: `schema-version\|schema_version\|content-type` | Medium |
| Outbox table or processor | All | regex: `outbox\|OutboxProcessor\|outbox_events` | High |
| Retry topic or x-death header | All | regex: `retry_count\|x-death\|retry-topic` | Medium |
| Correlation ID propagation | All | regex: `correlation[_-]?id\|correlationId` | Medium |
| Idempotency key in consumer | All | regex: `event_id\|message_id\|dedup\|processed_events` | Medium |
| Connection pooling / channel reuse | All | regex: `ConnectionPool\|channel\.pool\|sync\.Pool` | Medium |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| No broker client imports in async-heavy code that has background work | All | heuristic: presence of `async def` workers but no queue imports | Medium |
| Direct DB-to-DB sync calls in event-suggesting code (no queue) | All | heuristic: 3+ tables updated in sequence without an event publish | Low |
| No retry/DLQ configuration despite broker usage | All | regex absence: searched-for `retry\|dead-letter\|x-death` not found | Medium |
| No correlation_id propagation in cross-service calls | All | regex absence: `correlation_id` not in any handler | Low |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Kafka producer with `acks=0` | All | regex: `acks\s*[:=]\s*0` | High |
| Kafka producer without `enable.idempotence=true` when transactional | All | regex: `transactional\.id` without `enable\.idempotence` | High |
| RabbitMQ consumer with `auto_ack=True` | Python | regex: `auto_ack\s*=\s*True` | High |
| Kafka consumer with `autoCommit: true` for side-effecting work | TypeScript | regex: `autoCommit\s*:\s*true` | High |
| Prefetch count = 0 (unbounded) | All | regex: `prefetch_count\s*[:=]\s*0\|max.in.flight.requests.per.connection\s*=\s*[1-9]\d*\d*` | High |
| DLQ without TTL → infinite growth risk | All | regex: `x-dead-letter-exchange` without `x-message-ttl` | Medium |
| Synchronous publish inside DB transaction (no outbox) | Python, TS | regex: `with transaction\.\|BEGIN.*COMMIT` followed by `basic_publish\|producer\.send` within 20 lines | High |
| Hardcoded broker URL in source (not env) | All | regex: `amqp://[^"'\s]+\|kafka:[0-9]+\|sqs\.[a-z0-9-]+\.amazonaws` literal in code | High |
| No max retries on consumer | All | regex: absence of `max_retries\|retry_count\|retry-policy` near consume call | Medium |
| Queue declared without `durable=True` | Python, Go | regex: `queue_declare\([^)]*\)` without `durable\s*=\s*True` | High |
| Topic created with `replication.factor=1` in production config | All | regex: `replication\.factor\s*[:=]\s*1` | High |
| Missing connection retry/backoff | All | regex: absence of `retry\|backoff\|Reconnect` near connection setup | Medium |

## 5. Anti-Patterns

### Anti-Pattern: Auto-Ack Before Processing

**Description:** Consumer acknowledges a message before it has been processed.

```python
# ❌ WRONG
ch.basic_consume(queue='orders', on_message_callback=process, auto_ack=True)
```

**Why it's dangerous:** If the consumer crashes mid-process, the message is gone. RabbitMQ has already removed it from the queue. No retry, no DLQ, no recovery.

**Detection:** Regex `auto_ack\s*=\s*True` or `autoAck\s*[:=]\s*true` near `basic_consume` / `subscribe`.

**Fix:**
```python
# ✅ CORRECT
def cb(ch, method, props, body):
    try:
        process(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
ch.basic_qos(prefetch_count=10)
ch.basic_consume(queue='orders', on_message_callback=cb, auto_ack=False)
```

### Anti-Pattern: Publish Inside Database Transaction Without Outbox

**Description:** Producer writes to the DB and then publishes a message within the same code path, with no compensating mechanism.

```python
# ❌ WRONG
with db.begin():
    order = Order.create(...)
    ch.basic_publish(exchange='orders', body=json.dumps(order))
    # If basic_publish raises, transaction rolls back. But if it returns 0
    # (no confirms) and the broker silently drops the message, the order
    # is in the DB and no one will ever know.
```

**Why it's dangerous:** Two-phase commit (XA) is heavy and rare. Without an outbox, you get **dual-write inconsistency**: the DB row exists but the message is lost, or vice versa. This is the #1 source of "we processed the payment but never sent the confirmation email" bugs.

**Detection:** Look for `db.commit()` / `BEGIN` / `COMMIT` and `basic_publish` / `producer.send` within 20 lines and no `outbox` table reference.

**Fix:** Use the **transactional outbox pattern**. Write the event to an `outbox` table in the same DB transaction. A separate poller reads the outbox and publishes to the broker with confirms. After confirm, mark the row as published.

```python
# ✅ CORRECT — outbox write
with db.begin():
    order = Order.create(...)
    OutboxEvent.create(
        aggregate_type='Order',
        aggregate_id=order.id,
        event_type='order.created',
        payload=json.dumps(order.to_dict()),
    )

# Separate worker (transactional outbox poller)
while True:
    events = OutboxEvent.where(published=False).limit(100).all()
    for ev in events:
        try:
            producer.send(  # with publisher confirms
                topic='orders.created',
                key=ev.aggregate_id,
                value=ev.payload,
            ).get(timeout=10)
            ev.published = True
            ev.save()
        except KafkaException:
            break  # retry next tick
```

### Anti-Pattern: Unbounded Queue Depth

**Description:** No `max-length`, no TTL, no flow-control alarm. The queue can grow without limit.

**Why it's dangerous:** A runaway producer (or a dead consumer) can OOM the broker in minutes. A 100-GB broker disk filling silently is a multi-hour outage.

**Detection:** `queue_declare` without `x-max-length` or `x-message-ttl`; Kafka topic config without `retention.ms` or `retention.bytes`; CloudWatch/Stackdriver alarms missing on `ApproximateNumberOfMessagesVisible`.

**Fix:** Configure `x-max-length` (RabbitMQ), `retention.ms` and `retention.bytes` (Kafka), and a queue-depth alarm.

### Anti-Pattern: Requeue on Every Failure

**Description:** Consumer NACKs every failure with `requeue=True`.

```python
# ❌ WRONG
except Exception:
    ch.basic_nack(delivery_tag=tag, requeue=True)
```

**Why it's dangerous:** A poison-pill message (malformed JSON, missing required field) will be redelivered forever at the head of the queue, blocking every message behind it. CPU goes to 100%, queue grows, no one notices because "the consumer is running."

**Detection:** Regex `requeue\s*=\s*True` or absence of any retry-count / DLQ logic.

**Fix:** Use a retry counter (header `x-retry-count` or `x-death`); after N retries, publish to DLQ.

### Anti-Pattern: Synchronous Publish in Request Handler

**Description:** HTTP handler publishes to a broker and waits for the confirm before returning.

```typescript
// ❌ WRONG — 200 ms per request, blocks on broker
app.post('/orders', async (req, res) => {
  const order = await createOrder(req.body);
  await producer.send({ topic: 'orders.created', messages: [...] });  // wait
  res.json(order);
});
```

**Why it's dangerous:** Couples API latency to broker health. Broker slow = API slow. Broker down = API down. Defeats the purpose of async messaging.

**Detection:** `producer.send().get()` or `await producer.send()` inside an HTTP handler that is on the critical path.

**Fix:** Use the outbox pattern (write event in DB transaction; separate poller publishes). Or accept that this specific event is on the hot path and use the request timeout / circuit breaker to fail fast.

### Anti-Pattern: Tight Coupling Through Direct Queue Names

**Description:** Producer hardcodes the exact queue name; consumer subscribes to that exact queue. Renaming requires coordinated deploy.

```python
# ❌ WRONG
ch.basic_publish(exchange='', routing_key='order-fulfillment-queue-v2', body=...)
```

**Why it's dangerous:** No room for blue/green deploys, no room for routing logic, no room for replay. The producer and consumer are joined at the hip.

**Detection:** Hardcoded queue names in publish calls; absence of exchange/binding indirection.

**Fix:** Publish to a topic or exchange; let bindings route to the right physical queue(s). Version the topic name, not the queue.

### Anti-Pattern: Ignoring Publisher Confirms

**Description:** Producer uses fire-and-forget.

```python
# ❌ WRONG
ch.basic_publish(exchange='orders', body=msg)
return  # broker may never receive it
```

**Why it's dangerous:** Silent message loss. Worst-case failure mode of any queue-based system.

**Detection:** `basic_publish` without `confirm_delivery()` / `mandatory=True` upstream; Kafka producer missing `acks=-1`.

**Fix:** Enable confirms; treat any nack/unroutable as a hard failure with retry.

### Anti-Pattern: Big Messages

**Description:** Messages contain 5 MB JSON blobs of full database rows.

```python
# ❌ WRONG
producer.send('orders.created', value=json.dumps(get_full_order_with_every_relation()))
```

**Why it's dangerous:** Brokers have size limits (Kafka 1 MB default, SQS 256 KB, Pub/Sub 10 MB). Large messages hammer the broker's heap, garbage-collect slowly, and tie up partition leaders. Also a security and PII risk — every consumer sees every field.

**Detection:** Regex looking for `payload|body` exceeding expected sizes; static analysis of publish call argument length.

**Fix:** Send only an ID + event type; have consumers fetch the data they need. If you must send a payload, compress it (`gzip`, `snappy`) and keep it under 256 KB.

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `RABBITMQ_URL` | string | none | `amqps://user:pass@host:5671/vhost` | AMQP connection URI. Use TLS in production. |
| `RABBITMQ_PREFETCH_COUNT` | int | 0 (unbounded) | 10–100 | Max unacknowledged messages per consumer. Tune to processing latency. |
| `RABBITMQ_QUEUE_TTL_MS` | int | none | 3,600,000 | `x-message-ttl`. Messages older than this go to DLX. |
| `RABBITMQ_QUEUE_MAX_LENGTH` | int | none | 100,000 | `x-max-length`. Hard cap on queue depth. |
| `KAFKA_BOOTSTRAP_SERVERS` | string | none | `kafka-0:9092,kafka-1:9092,kafka-2:9092` | Comma-separated broker list. Min 3 for HA. |
| `KAFKA_ACKS` | string | `1` | `all` | `0`=fire-forget, `1`=leader-only, `all`=full ISR. Use `all` for durability. |
| `KAFKA_RETENTION_MS` | int | 604,800,000 | varies | 7 days default. 1–30 days for event sourcing; 7+ for audit. |
| `KAFKA_REPLICATION_FACTOR` | int | 1 | 3 | Topic RF. 1 = no HA. Production min 3. |
| `KAFKA_MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION` | int | 5 | 5 | Cap concurrent in-flight per broker connection. Must be ≤ 5 with idempotence. |
| `KAFKA_COMPRESSION_TYPE` | string | `none` | `zstd` or `snappy` | Reduces network/disk at minor CPU cost. |
| `KAFKA_LINGER_MS` | int | 0 | 5–50 | Batching delay. Higher = better throughput, higher latency. |
| `SQS_VISIBILITY_TIMEOUT` | int | 30 | 60–300 | Seconds a message is invisible after receive. Should be ≥ 2× processing time. |
| `SQS_MESSAGE_RETENTION_PERIOD` | int | 345,600 (4 days) | 345,600 | Max time SQS keeps a message. |
| `SQS_MAX_RECEIVE_COUNT` (via redrive) | int | 5 | 3–10 | How many times a message can be received before DLQ. |
| `PUBSUB_ACK_DEADLINE` | int | 10 | 30–60 | Seconds to ack a pulled message before redelivery. |
| `OUTBOX_POLL_INTERVAL_MS` | int | 1000 | 500–5000 | How often the outbox poller scans for unpublished events. |
| `OUTBOX_BATCH_SIZE` | int | 100 | 100–1000 | Rows per outbox poller batch. |

## 7. Integration Points

- **Depends on:** A broker (RabbitMQ/Kafka/SQS/Pub/Sub) with adequate disk and replication. Schema registry (if using Avro/Protobuf). Observability stack (Prometheus + OTel). DNS / service discovery to find brokers.
- **Used by:** API services (publishing domain events), background workers (consuming jobs), stream processors (Kafka Streams, ksqlDB, Apache Flink), schedulers (sending delayed jobs to delayed-message exchanges).
- **Related concepts:**
  - **`foundation.fault-tolerance`:** queues are the canonical mechanism for absorbing downstream outages via buffering + retry. Pair with circuit breakers to fail-fast on a sick downstream rather than spinning on retries.
  - **`foundation.idempotency`:** at-least-once delivery means consumers must dedupe. Pair with a `processed_events` table or unique constraint.
  - **`foundation.circuit-breaker`:** wrap downstream calls inside a consumer. If the downstream is sick, open the circuit and let the message go to retry/DLQ instead of holding the queue.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| `mq_publish_total` / `mq_consume_total` | Prometheus | rate-based | Plot rate; alert on drops > 50% in 5 min |
| `mq_publish_error_total` | Prometheus | > 1% for 5 min → warn; > 5% → page | Check broker health, network, credentials |
| `mq_queue_depth` (RabbitMQ `queue_messages_ready`) | Prometheus | > 100k → warn; > 500k → page | Scale consumers or reduce produce rate |
| `mq_oldest_message_age_seconds` | Prometheus | > 300 → warn; > 1800 → page | Consumer stuck or down |
| `mq_consumer_lag` (Kafka) | Prometheus | > 10000 → warn; > 60000 → page | Scale consumer group |
| `mq_dlq_depth` | Prometheus | > 0 → page | Data is being lost; investigate immediately |
| `mq_dlq_growth_rate` | Prometheus | > 0/min for 10 min → page | Sustained processing failure |
| `mq_consumer_duration_seconds` p99 | Prometheus | exceeds SLO → page | Slow downstream or large payloads |
| `mq_redelivery_total` | Prometheus | > 5% of consume → warn | Crashes, timeouts, or poison pills |
| `mq_consumer_connections` | Prometheus | drop to 0 → page | Consumers crashed or partitioned off |
| `mq_broker_disk_free` | Prometheus | < 20% → page | Disk full = total outage |

## 9. Evolution / Version Tracking

**Original approach (1990s–early 2000s):** Point-to-point integration via CORBA, DCOM, Java RMI, raw socket protocols. Each producer knew its consumers. Adding a new consumer required touching every producer. Failures cascaded synchronously.

**First-generation brokers (mid-2000s):** RabbitMQ (2007), ActiveMQ (2004), and the AMQP 0-9-1 standard introduced broker-mediated routing with exchanges, bindings, and acknowledgments. The "enterprise service bus" pattern emerged. These were excellent for task distribution and RPC-style async but limited for high-throughput event streams.

**Log-based second generation (2011+):** LinkedIn open-sourced Kafka in 2011. The fundamental insight: store messages as an immutable, partitioned, ordered log; let consumers track their own offset. This enabled replay-from-any-point, multi-subscriber fan-out without message duplication, and throughput orders of magnitude higher than AMQP brokers. Confluent (founded by Kafka's creators) commercialized it with Schema Registry and ksqlDB. AWS MSK and Confluent Cloud are now the dominant managed offerings.

**Cloud-native third generation (2010s+):** AWS SQS (2006) and SNS (2010), Google Pub/Sub, Azure Service Bus. Managed queues with no operational burden; per-message pricing; integration with the rest of the cloud. The trade-off: less control over ordering, replay, and throughput characteristics.

**Emerging patterns (2020s):**
- **CloudEvents** (CNCF standard) — a vendor-neutral envelope format that travels with the message through any broker.
- **Kafka Streams / ksqlDB / Flink** — turning the queue into a database by treating the log as the source of truth (event sourcing + CQRS).
- **Redpanda, Pulsar, NATS JetStream** — alternatives that target Kafka's API surface with different operational footprints (Redpanda: single binary, no ZooKeeper; Pulsar: tiered storage; NATS: lightweight, no disk dependency).
- **WASM-filtered queues** — run filtering logic inside the broker to avoid pulling every message into the consumer (Pulsar Functions, NATS subjects with wildcard subscriptions, AWS SNS message filtering).

**Deprecated patterns:** Manual acknowledgment at the application level without broker-level acks; using a database table as a queue (`SELECT ... FOR UPDATE SKIP LOCKED` polled by workers — works but cannot scale to millions of msg/s and lacks DLQ, observability, and replay); "ESB" patterns that route everything through a central hub (replaced by smart endpoints / dumb pipes).

## 10. References

- RabbitMQ official docs — https://www.rabbitmq.com/docs/
- Apache Kafka official docs — https://kafka.apache.org/documentation/
- AWS SQS Developer Guide — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/
- Google Cloud Pub/Sub documentation — https://cloud.google.com/pubsub/docs
- CNCF CloudEvents spec — https://github.com/cloudevents/spec
- Confluent Schema Registry — https://docs.confluent.io/platform/current/schema-registry/
- Microsoft Azure Well-Architected: Messaging — https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/messaging
- "Designing Data-Intensive Applications" by Martin Kleppmann, chapter 11 (Stream Processing)
- "Enterprise Integration Patterns" by Gregor Hohpe and Bobby Woolf
- RabbitMQ Publisher Confirms — https://www.rabbitmq.com/docs/confirms
- Kafka Exactly-Once Semantics — https://kafka.apache.org/documentation/#semantics
- "Transactional Outbox Pattern" — https://microservices.io/patterns/data/transactional-outbox.html
