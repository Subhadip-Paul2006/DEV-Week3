#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <semaphore.h>

#define SHM_NAME "/sdat_example_shm"
#define SHM_SIZE 1024

typedef struct {
    sem_t mutex;
    int counter;
    char message[256];
} shared_data_t;

int setup_shared_memory(void) {
    int shm_fd = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
    if (shm_fd < 0) {
        return -1;
    }

    if (ftruncate(shm_fd, SHM_SIZE) < 0) {
        close(shm_fd);
        return -1;
    }

    shared_data_t *data = (shared_data_t*)mmap(NULL, SHM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);
    if (data == MAP_FAILED) {
        close(shm_fd);
        return -1;
    }

    sem_init(&(data->mutex), 1, 1);
    data->counter = 0;

    // Critical section with semaphore
    sem_wait(&(data->mutex));
    data->counter++;
    sem_post(&(data->mutex));

    munmap(data, SHM_SIZE);
    close(shm_fd);
    return 0;
}
