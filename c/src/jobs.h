#ifndef JOBS_H
#define JOBS_H
#include <sys/types.h>
/* Register an already-forked child; returns job number, or -1 on allocation failure. */
int jobs_add(pid_t pid, const char *command);
/* Nonblocking reap; completed_only=1 prints only Done notifications.
 * Call before the next prompt; jobs builtin calls with 0. */
void jobs_list(int completed_only);
/* Release bookkeeping on shell exit. Does not kill live children. */
void jobs_clear(void);
#endif
