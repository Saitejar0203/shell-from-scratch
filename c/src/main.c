#include "shell.h"
#include <readline/readline.h>
#include "completion.h"
#include "jobs.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>

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
    if (!strcmp(command, "jobs")) { jobs_list(0); return 1; }
    if (!strcmp(command, "complete")) { completion_builtin((int)args.count, args.words); return 1; }
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
            if (!strcmp(name,"echo") || !strcmp(name,"exit") || !strcmp(name,"type") || !strcmp(name,"pwd") || !strcmp(name,"cd") || !strcmp(name,"complete") || !strcmp(name,"jobs"))
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
static int redirect(Words *args, int saved[3]) {
    for (int fd = 0; fd < 3; fd++) saved[fd] = -1;
    for (size_t i = 0; i < args->count;) {
        if (!args->operators[i]) { i++; continue; }
        if (i + 1 >= args->count || args->operators[i+1]) {
            fprintf(stderr, "shell: missing redirection filename\n"); return 0;
        }
        int fd = args->words[i][0] == '2' ? 2 : 1;
        int mode = strstr(args->words[i], ">>") ? O_APPEND : O_TRUNC;
        int file = open(args->words[i+1], O_WRONLY | O_CREAT | mode, 0666);
        if (file < 0) { perror(args->words[i+1]); return 0; }
        if (saved[fd] < 0) saved[fd] = dup(fd);
        if (saved[fd] < 0 || dup2(file, fd) < 0) { perror("redirect"); close(file); return 0; }
        close(file);
        free(args->words[i]); free(args->words[i+1]);
        memmove(args->words+i, args->words+i+2, (args->count-i-1)*sizeof(char*));
        memmove(args->operators+i, args->operators+i+2, args->count-i-2);
        args->count -= 2;
    }
    return 1;
}
static void restore(int saved[3]) {
    fflush(NULL);
    for (int fd=0; fd<3; fd++) if (saved[fd]>=0) { dup2(saved[fd],fd); close(saved[fd]); }
}
static void pipeline(Words args) {
    size_t stages = 1;
    for (size_t i=0; i<args.count; i++) if (args.operators[i] == 3) {
        if (!i || i+1==args.count || args.operators[i-1]==3) {
            fputs("shell: empty pipeline stage\n", stderr); return;
        }
        stages++;
    }
    pid_t *children = allocate(stages * sizeof(*children));
    size_t started = 0, begin = 0;
    int previous = -1;
    fflush(NULL);
    for (size_t stage=0; stage<stages; stage++) {
        size_t end = begin;
        while (end<args.count && args.operators[end]!=3) end++;
        Words command = {allocate((end-begin+1)*sizeof(char*)), allocate(end-begin+1), end-begin};
        memcpy(command.words,args.words+begin,command.count*sizeof(char*));
        memcpy(command.operators,args.operators+begin,command.count);
        command.words[command.count]=NULL;
        int descriptors[2] = {-1,-1};
        if (stage+1<stages && pipe(descriptors)<0) {
            perror("pipe"); free(command.words); free(command.operators); break;
        }
        pid_t child=fork();
        if (child==0) {
            if (previous>=0) { if (dup2(previous,STDIN_FILENO)<0) _exit(1); close(previous); }
            if (descriptors[1]>=0) {
                close(descriptors[0]);
                if (dup2(descriptors[1],STDOUT_FILENO)<0) _exit(1);
                close(descriptors[1]);
            }
            int saved[3];
            if (!redirect(&command,saved) || !command.count) _exit(1);
            int handled = builtin(command);
            if (handled) { fflush(NULL); _exit(0); }
            char *path=find_executable(command.words[0]);
            if (path) execv(path,command.words);
            fprintf(stderr,"%s: command not found\n",command.words[0]);
            _exit(127);
        }
        free(command.words); free(command.operators);
        if (previous>=0) close(previous);
        if (descriptors[1]>=0) close(descriptors[1]);
        previous=descriptors[0];
        if (child<0) { perror("fork"); break; }
        children[started++]=child;
        begin=end+1;
    }
    if (previous>=0) close(previous);
    for (size_t i=0;i<started;i++) while (waitpid(children[i],NULL,0)<0 && errno==EINTR) {}
    free(children);
}
int main(void) {
    setbuf(stdout, NULL);
    char *line = NULL; size_t capacity = 0;
    int interactive = isatty(STDIN_FILENO) && isatty(STDOUT_FILENO);
    if (interactive) completion_initialize();
    for (;;) {
        jobs_list(1);
        if (interactive) { free(line); line = readline("$ "); if (!line) break; }
        else { printf("$ "); if (getline(&line, &capacity, stdin) < 0) break; }
        Words args = parse(line);
        if (!args.count) { free_words(args); continue; }
        int has_pipe = 0;
        for (size_t i=0;i<args.count;i++) if (args.operators[i]==3) has_pipe=1;
        if (has_pipe) { pipeline(args); free_words(args); continue; }
        int background = args.count && args.operators[args.count-1] == 2;
        if (background) { free(args.words[--args.count]); args.words[args.count] = NULL; }
        int job_id = 0; pid_t job_pid = -1;
        int saved[3];
        if (!redirect(&args, saved) || !args.count) { restore(saved); free_words(args); continue; }
        int handled = builtin(args);
        if (handled == 2) { restore(saved); free_words(args); break; }
        if (!handled) {
            char *path = find_executable(args.words[0]);
            if (!path) printf("%s: command not found\n", args.words[0]);
            else {
                pid_t child = fork();
                if (!child) { execv(path, args.words); perror(args.words[0]); _exit(127); }
                if (child > 0) {
                    if (background) { job_id = jobs_add(child, line); job_pid = child; }
                    else while (waitpid(child, NULL, 0) < 0 && errno == EINTR) {}
                }
                else perror("fork");
                free(path);
            }
        }
        restore(saved);
        if (job_id > 0) printf("[%d] %ld\n", job_id, (long)job_pid);
        free_words(args);
    }
    free(line); jobs_clear(); completion_cleanup(); return 0;
}
