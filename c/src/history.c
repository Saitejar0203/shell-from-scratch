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

static int read_entries(const char *path) {
    FILE *stream = fopen(path, "r");
    if (!stream) return -1;
    char *line = NULL;
    size_t allocated = 0;
    ssize_t length;
    int result = 0;
    while ((length = getline(&line, &allocated, stream)) >= 0) {
        while (length && (line[length - 1] == '\n' || line[length - 1] == '\r'))
            line[--length] = '\0';
        /* File reads are recallable but never pending session appends. */
        if (add_entry(line, 0) < 0) { result = -1; break; }
    }
    if (ferror(stream)) result = -1;
    int saved_errno = errno;
    free(line);
    if (fclose(stream) != 0 && result == 0) return -1;
    errno = saved_errno;
    return result;
}

static int write_entries(const char *path, int append) {
    FILE *stream = fopen(path, append ? "a" : "w");
    if (!stream) return -1;
    int result = 0;
    for (size_t i = 0; i < count; i++) {
        if ((!append || entries[i].pending) &&
            (fputs(entries[i].line, stream) == EOF || fputc('\n', stream) == EOF)) {
            result = -1; break;
        }
    }
    int saved_errno = errno;
    if (fclose(stream) != 0) return -1;
    if (result < 0) { errno = saved_errno; return -1; }
    /* -w deliberately does not consume the append queue, matching Python. */
    if (append) for (size_t i = 0; i < count; i++) entries[i].pending = 0;
    return 0;
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
    if (argc > 1 && !strcmp(argv[1], "-w")) {
        if (argc != 3) { fprintf(stderr,"history: -w requires a path\n"); return 1; }
        if (write_entries(argv[2],0) < 0) { perror("history"); return 1; }
        return 0;
    }
    if (argc > 1 && !strcmp(argv[1], "-r")) {
        if (argc != 3) { fprintf(stderr,"history: -r requires a path\n"); return 1; }
        if (read_entries(argv[2]) < 0) { perror("history"); return 1; }
        return 0;
    }
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
