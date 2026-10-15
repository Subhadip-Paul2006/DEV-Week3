package main

import (
	"context"
	"net"
	"sync"
	"time"

	"github.com/cenkalti/backoff/v4"
	"github.com/ethereum/go-ethereum/ethclient"
	"go.uber.org/zap"
)

type JobQueue struct {
	jobs   chan string
	wg     sync.WaitGroup
	logger *zap.Logger
}

func NewJobQueue(logger *zap.Logger, bufferSize int) *JobQueue {
	return &JobQueue{
		jobs:   make(chan string, bufferSize),
		logger: logger,
	}
}

func (q *JobQueue) StartWorkers(ctx context.Context, count int) {
	for i := 0; i < count; i++ {
		q.wg.Add(1)
		go func(workerID int) {
			defer q.wg.Done()
			for {
				select {
				case <-ctx.Done():
					q.logger.Info("Worker stopping on context cancellation")
					return
				case job, ok := <-q.jobs:
					if !ok {
						return
					}
					q.processWithRetry(ctx, job)
				}
			}
		}(i)
	}
}

func (q *JobQueue) processWithRetry(ctx context.Context, job string) error {
	operation := func() error {
		// Simulating external operation
		return nil
	}

	expBackoff := backoff.NewExponentialBackOff()
	expBackoff.MaxElapsedTime = 10 * time.Second

	return backoff.Retry(operation, backoff.WithContext(expBackoff, ctx))
}

func (q *JobQueue) Submit(job string) {
	q.jobs <- job
}

func (q *JobQueue) Close() {
	close(q.jobs)
	q.wg.Wait()
}

func StartP2PListener(addr string) (net.Listener, error) {
	return net.Listen("tcp", addr)
}

func ConnectBlockchainClient(rawURL string) (*ethclient.Client, error) {
	return ethclient.Dial(rawURL)
}

