#include "shell.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <errno.h>

static char *find_executable(const char *name) {
    if (strchr(name, '/')) {
        struct stat st;
        return !stat(name, &st) && S_ISREG(st.st_mode) && !access(name, X_OK) ? strdup(name) : NULL;
    }
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

static int builtin(Words args) {
    const char *command = args.words[0];
    if (!strcmp(command, "exit")) return 2;
    if (!strcmp(command, "echo")) {
        for (size_t i = 1; i < args.count; i++) printf("%s%s", i > 1 ? " " : "", args.words[i]);
        putchar('\n');
    } else if (!strcmp(command, "pwd")) {
        char *cwd = getcwd(NULL, 0);
        if (cwd) { puts(cwd); free(cwd); } else perror("pwd");
    } else if (!strcmp(command, "cd")) {
        char *dir = args.count > 1 ? args.words[1] : getenv("HOME");
        if (dir && !strcmp(dir, "~")) dir = getenv("HOME");
        if (dir && chdir(dir)) fprintf(stderr, "cd: %s: %s\n", dir, strerror(errno));
    } else if (!strcmp(command, "type")) {
        if (args.count > 1) {
            char *name = args.words[1];
            if (!strcmp(name,"echo") || !strcmp(name,"exit") || !strcmp(name,"type") || !strcmp(name,"pwd") || !strcmp(name,"cd"))
                printf("%s is a shell builtin\n", name);
            else {
                char *path = find_executable(name);
                if (path) { printf("%s is %s\n", name, path); free(path); }
                else printf("%s: not found\n", name);
            }
        }
    } else return 0;
    return 1;
}
int main(void) {
    setbuf(stdout, NULL);
    char *line = NULL; size_t capacity = 0;
    while (printf("$ "), getline(&line, &capacity, stdin) >= 0) {
        Words args = parse(line);
        if (!args.count) { free_words(args); continue; }
        int handled = builtin(args);
        if (handled == 2) { free_words(args); break; }
        if (!handled) {
            char *path = find_executable(args.words[0]);
            if (!path) printf("%s: command not found\n", args.words[0]);
            else {
                pid_t child = fork();
                if (!child) { execv(path, args.words); perror(args.words[0]); _exit(127); }
                if (child > 0) { while (waitpid(child, NULL, 0) < 0 && errno == EINTR) {} }
                else perror("fork");
                free(path);
            }
        }
        free_words(args);
    }
    free(line); return 0;
}
