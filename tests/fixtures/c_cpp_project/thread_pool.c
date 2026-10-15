#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <syslog.h>
#include "thread_pool.h"

struct thread_pool {
    pthread_t *threads;
    int num_threads;
    int *queue;
    int queue_size;
    int queue_head;
    int queue_tail;
    int count;
    pthread_mutex_t lock;
    pthread_cond_t notify;
    int shutdown;
};

static void* thread_worker(void *arg) {
    thread_pool_t *pool = (thread_pool_t*)arg;
    while (1) {
        pthread_mutex_lock(&(pool->lock));
        while ((pool->count == 0) && (!pool->shutdown)) {
            pthread_cond_wait(&(pool->notify), &(pool->lock));
        }

        if (pool->shutdown) {
            pthread_mutex_unlock(&(pool->lock));
            pthread_exit(NULL);
        }

        int client_fd = pool->queue[pool->queue_head];
        pool->queue_head = (pool->queue_head + 1) % pool->queue_size;
        pool->count--;

        pthread_mutex_unlock(&(pool->lock));

        // Process connection
        syslog(LOG_INFO, "Processing request on fd %d", client_fd);
        close(client_fd);
    }
    return NULL;
}

thread_pool_t* thread_pool_create(int num_threads) {
    thread_pool_t *pool = (thread_pool_t*)malloc(sizeof(thread_pool_t));
    pool->num_threads = num_threads;
    pool->queue_size = 256;
    pool->queue_head = 0;
    pool->queue_tail = 0;
    pool->count = 0;
    pool->shutdown = 0;

    pool->threads = (pthread_t*)malloc(sizeof(pthread_t) * num_threads);
    pool->queue = (int*)malloc(sizeof(int) * pool->queue_size);

    pthread_mutex_init(&(pool->lock), NULL);
    pthread_cond_init(&(pool->notify), NULL);

    for (int i = 0; i < num_threads; i++) {
        pthread_create(&(pool->threads[i]), NULL, thread_worker, (void*)pool);
    }

    return pool;
}

void thread_pool_submit(thread_pool_t *pool, int client_fd) {
    pthread_mutex_lock(&(pool->lock));
    if (pool->count < pool->queue_size) {
        pool->queue[pool->queue_tail] = client_fd;
        pool->queue_tail = (pool->queue_tail + 1) % pool->queue_size;
        pool->count++;
        pthread_cond_signal(&(pool->notify));
    }
    pthread_mutex_unlock(&(pool->lock));
}

void thread_pool_destroy(thread_pool_t *pool) {
    pthread_mutex_lock(&(pool->lock));
    pool->shutdown = 1;
    pthread_cond_broadcast(&(pool->notify));
    pthread_mutex_unlock(&(pool->lock));

    for (int i = 0; i < pool->num_threads; i++) {
        pthread_join(pool->threads[i], NULL);
    }

    free(pool->threads);
    free(pool->queue);
    pthread_mutex_destroy(&(pool->lock));
    pthread_cond_destroy(&(pool->notify));
    free(pool);
}
