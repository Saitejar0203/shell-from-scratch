#define _POSIX_C_SOURCE 200809L
#include "history.h"
#include <ctype.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <readline/history.h>

typedef struct {
    char *line;
    int pending;
} Entry;

static Entry *entries;
static size_t count, capacity;
static char *startup_path;

static int nonblank(const char *line) {
    for (; *line; line++) if (!isspace((unsigned char)*line)) return 1;
    return 0;
}

static int add_entry(const char *line, int pending) {
    if (!nonblank(line)) return 0;
    if (count == capacity) {
        size_t next = capacity ? capacity * 2 : 64;
        if (next < capacity || next > SIZE_MAX / sizeof(*entries)) {
            errno = ENOMEM; return -1;
        }
        Entry *grown = realloc(entries, next * sizeof(*entries));
        if (!grown) return -1;
        entries = grown; capacity = next;
    }
    char *copy = strdup(line);
    if (!copy) return -1;
    entries[count++] = (Entry){copy, pending};
    add_history(copy); /* GNU Readline and macOS libedit both copy this string. */
    return 0;
}

void history_record(const char *line) {
    if (line && add_entry(line, 1) < 0) perror("history");
}

void history_cleanup(void) {
    for (size_t i = 0; i < count; i++) free(entries[i].line);
    free(entries); free(startup_path);
    entries = NULL; startup_path = NULL; count = capacity = 0;
    clear_history();
}

void history_load_startup(void) { using_history(); history_cleanup(); }
void history_save_exit(void) {}
int history_builtin(int argc, char **argv) {
    size_t requested = count;
    if (argc > 1) {
        if (argc != 2 || !*argv[1]) goto invalid_count;
        requested = 0;
        for (const unsigned char *p = (const unsigned char *)argv[1]; *p; p++) {
            if (!isdigit(*p)) goto invalid_count;
            unsigned digit = *p - '0';
            requested = requested > (SIZE_MAX - digit) / 10 ? SIZE_MAX : requested * 10 + digit;
        }
    }
    size_t start = requested < count ? count - requested : 0;
    for (size_t i = start; i < count; i++) printf("%5zu  %s\n", i + 1, entries[i].line);
    return ferror(stdout) ? 1 : 0;
invalid_count:
    fprintf(stderr, "history: expected a non-negative count\n");
    return 1;
}
