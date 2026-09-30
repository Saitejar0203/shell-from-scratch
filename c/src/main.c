#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    setbuf(stdout, NULL);
    char *line = NULL;
    size_t capacity = 0;
    while (printf("$ "), getline(&line, &capacity, stdin) >= 0) {
        char *save = NULL;
        char *command = strtok_r(line, " \t\r\n", &save);
        if (!command) continue;
        if (!strcmp(command, "exit")) break;
        if (!strcmp(command, "echo")) {
            char *word; int first = 1;
            while ((word = strtok_r(NULL, " \t\r\n", &save))) {
                printf("%s%s", first ? "" : " ", word);
                first = 0;
            }
            putchar('\n');
        } else if (!strcmp(command, "type")) {
            char *name = strtok_r(NULL, " \t\r\n", &save);
            if (name) {
                if (!strcmp(name, "echo") || !strcmp(name, "exit") || !strcmp(name, "type"))
                    printf("%s is a shell builtin\n", name);
                else printf("%s: not found\n", name);
            }
        } else {
            printf("%s: command not found\n", command);
        }
    }
    free(line);
    return 0;
}
