#ifndef SHELL_COMPLETION_H
#define SHELL_COMPLETION_H
void completion_initialize(void);
/* argc/argv include argv[0] == "complete". */
int completion_builtin(int argc, char **argv);
void completion_cleanup(void);
#endif
