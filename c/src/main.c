#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <errno.h>

static char *find_executable(const char *name) {
    const char *value = getenv("PATH");
    if (!value) return NULL;
    char *paths = strdup(value), *cursor = paths, *directory;
    while ((directory = strsep(&cursor, ":"))) {
        size_t size = strlen(directory) + strlen(name) + 3;
        char *path = malloc(size);
        snprintf(path, size, "%s/%s", *directory ? directory : ".", name);
        struct stat st;
        if (!stat(path, &st) && S_ISREG(st.st_mode) && !access(path, X_OK)) {
            free(paths); return path;
        }
        free(path);
    }
    free(paths); return NULL;
}

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
                else {
                    char *path = find_executable(name);
                    if (path) { printf("%s is %s\n", name, path); free(path); }
                    else printf("%s: not found\n", name);
                }
            }
        } else {
            char *path = find_executable(command);
            if (!path) { printf("%s: command not found\n", command); continue; }
            size_t count = 1, allocated = 8;
            char **args = malloc(allocated * sizeof(*args));
            args[0] = command;
            char *word;
            while ((word = strtok_r(NULL, " \t\r\n", &save))) {
                if (count + 1 == allocated) {
                    allocated *= 2; args = realloc(args, allocated * sizeof(*args));
                }
                args[count++] = word;
            }
            args[count] = NULL;
            pid_t child = fork();
            if (child == 0) {
                execv(path, args); perror(command); _exit(127);
            }
            if (child > 0) while (waitpid(child, NULL, 0) < 0 && errno == EINTR) {}
            else if (child < 0) perror("fork");
            free(args); free(path);
        }
    }
    free(line);
    return 0;
}
