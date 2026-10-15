#ifndef CONFIG_H
#define CONFIG_H

#include <stdlib.h>

#define PORT 8080
#define BUFFER_SIZE 4096

static inline const char* get_database_url(void) {
    const char *url = getenv("DATABASE_URL");
    if (!url) {
        return "postgres://localhost:5432/app";
    }
    return url;
}

#endif /* CONFIG_H */
