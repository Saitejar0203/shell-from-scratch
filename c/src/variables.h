#ifndef VARIABLES_H
#define VARIABLES_H

/* argc/argv include "declare" at argv[0]. Returns a shell-style exit status. */
int variables_builtin(int argc, char **argv);
/* Borrowed value; valid until that variable is changed or variables_clear().
 * Missing names return "". These variables are shell-local, not environment. */
const char *variable_get(const char *name);
void variables_clear(void);

#endif
