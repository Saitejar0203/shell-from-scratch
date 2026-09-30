#include "jobs.h"
#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

typedef struct Job {
    int id;
    pid_t pid;
    char *command;
    struct Job *next;
} Job;
static Job *jobs;

int jobs_add(pid_t pid, const char *command) {
    Job **tail = &jobs;
    int id = 1;
    while (*tail) {
        if ((*tail)->id == INT_MAX) { errno = EOVERFLOW; return -1; }
        id = (*tail)->id + 1; tail = &(*tail)->next;
    }
    while (isspace((unsigned char)*command)) command++;
    size_t n = strlen(command);
    while (n && isspace((unsigned char)command[n - 1])) n--;
    Job *j = malloc(sizeof(*j));
    if (!j) return -1;
    j->command = malloc(n + 1);
    if (!j->command) { free(j); return -1; }
    memcpy(j->command, command, n); j->command[n] = 0;
    j->pid = pid; j->id = id; j->next = NULL; *tail = j;
    return id;
}

void jobs_list(int completed_only) {
    int newest = 0, previous = 0;
    for (Job *j = jobs; j; j = j->next) { previous = newest; newest = j->id; }
    Job **slot = &jobs;
    while (*slot) {
        Job *j = *slot;
        int status;
        pid_t result;
        do { result = waitpid(j->pid, &status, WNOHANG); }
        while (result < 0 && errno == EINTR);
        int done = result == j->pid || (result < 0 && errno == ECHILD);
        if (!completed_only || done) {
            char marker = j->id == newest ? '+' : j->id == previous ? '-' : ' ';
            if (done) {
                size_t n = strlen(j->command);
                if (n && j->command[n - 1] == '&') n--;
                while (n && isspace((unsigned char)j->command[n - 1])) n--;
                j->command[n] = 0;
            }
            printf("[%d]%c  %-24s%s\n", j->id, marker, done ? "Done" : "Running", j->command);
        }
        if (done) {
            *slot = j->next; free(j->command); free(j);
        } else slot = &j->next;
    }
}

void jobs_clear(void) {
    while (jobs) {
        Job *next = jobs->next;
        (void)waitpid(jobs->pid, NULL, WNOHANG);
        free(jobs->command); free(jobs); jobs = next;
    }
}
