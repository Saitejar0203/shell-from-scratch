#ifndef SHELL_HISTORY_H
#define SHELL_HISTORY_H

/* Call once before the prompt loop, and save once on exit/EOF. */
void history_load_startup(void);
void history_save_exit(void);
/* Record nonblank input before dispatch, so history includes its own command. */
void history_record(const char *line);
/* argc/argv include argv[0] == "history"; returns a shell exit status. */
int history_builtin(int argc, char **argv);
/* Optional cleanup for embedding/tests; does not persist pending entries. */
void history_cleanup(void);

#endif
