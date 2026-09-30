#include <stdlib.h>
#include <string.h>
#include <readline/readline.h>
static char *builtin_candidate(const char *text, int state) {
    static size_t index;
    static const char *names[] = {"echo", "exit", "type", "pwd", "cd", NULL};
    if (!state) index = 0;
    while (names[index]) {
        const char *name = names[index++];
        if (!strncmp(name, text, strlen(text))) return strdup(name);
    }
    return NULL;
}
static char **complete_word(const char *text, int start, int end) {
    (void)end;
    rl_attempted_completion_over = 1;
    return start == 0 ? rl_completion_matches(text, builtin_candidate) : NULL;
}
void completion_initialize(void) {
    rl_attempted_completion_function = complete_word;
    rl_bind_key('\t', rl_complete);
}
