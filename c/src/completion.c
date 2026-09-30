#define _POSIX_C_SOURCE 200809L
#include "completion.h"
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <readline/readline.h>

typedef struct { char **items; size_t count, capacity; } Strings;
typedef struct Specification { char *command, *script; struct Specification *next; } Specification;
static Specification *specifications;
static Strings matches;
static size_t match_index;
static const char *builtins[] = {"echo", "exit", "pwd", "type", "cd", "jobs", "history", "declare", "complete"};

static void clear_strings(Strings *s) {
    for (size_t i = 0; i < s->count; i++) free(s->items[i]);
    free(s->items); *s = (Strings){0};
}
static int add_string(Strings *s, const char *text) {
    if (s->count == s->capacity) {
        size_t capacity = s->capacity ? s->capacity * 2 : 32;
        char **items = realloc(s->items, capacity * sizeof(*items));
        if (!items) return -1;
        s->items = items; s->capacity = capacity;
    }
    char *copy = strdup(text);
    if (!copy) return -1;
    s->items[s->count++] = copy; return 0;
}
static int compare_strings(const void *a, const void *b) {
    return strcmp(*(char *const *)a, *(char *const *)b);
}
static void sort_unique(Strings *s) {
    if (s->count < 2) return;
    qsort(s->items, s->count, sizeof(*s->items), compare_strings);
    size_t out = 1;
    for (size_t i = 1; i < s->count; i++) {
        if (!strcmp(s->items[out - 1], s->items[i])) free(s->items[i]);
        else s->items[out++] = s->items[i];
    }
    s->count = out;
}
static char *join(const char *directory, const char *name) {
    size_t a = strlen(directory), b = strlen(name);
    char *path = malloc(a + b + 2);
    if (!path) return NULL;
    memcpy(path, directory, a);
    if (a && directory[a - 1] != '/') path[a++] = '/';
    memcpy(path + a, name, b + 1); return path;
}
static int starts_with(const char *value, const char *prefix) {
    return strncmp(value, prefix, strlen(prefix)) == 0;
}
static Specification *find_specification(const char *command) {
    for (Specification *s = specifications; s; s = s->next)
        if (!strcmp(s->command, command)) return s;
    return NULL;
}
static void command_matches(const char *prefix, Strings *out) {
    for (size_t i = 0; i < sizeof(builtins) / sizeof(*builtins); i++)
        if (starts_with(builtins[i], prefix)) add_string(out, builtins[i]);
    const char *environment = getenv("PATH");
    char *path = strdup(environment ? environment : "");
    if (!path) return;
    char *part = path;
    for (;;) {
        char *separator = strchr(part, ':');
        if (separator) *separator = 0;
        const char *directory = *part ? part : ".";
        DIR *stream = opendir(directory);
        if (stream) {
            struct dirent *entry;
            while ((entry = readdir(stream))) {
                if (!starts_with(entry->d_name, prefix)) continue;
                char *full = join(directory, entry->d_name);
                struct stat st;
                if (full && stat(full, &st) == 0 && S_ISREG(st.st_mode) && access(full, X_OK) == 0)
                    add_string(out, entry->d_name);
                free(full);
            }
            closedir(stream);
        }
        if (!separator) break;
        part = separator + 1;
    }
    free(path);
}
static void file_matches(const char *text, Strings *out) {
    const char *slash = strrchr(text, '/');
    size_t directory_len = slash ? (size_t)(slash - text) + 1 : 0;
    const char *prefix = text + directory_len;
    char *typed = strndup(text, directory_len);
    if (!typed) return;
    DIR *stream = opendir(*typed ? typed : ".");
    if (stream) {
        struct dirent *entry;
        while ((entry = readdir(stream))) {
            if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..") ||
                !starts_with(entry->d_name, prefix)) continue;
            char *candidate = join(typed, entry->d_name);
            struct stat st;
            if (candidate && stat(candidate, &st) == 0) {
                if (S_ISDIR(st.st_mode)) {
                    size_t len = strlen(candidate);
                    char *directory = realloc(candidate, len + 2);
                    if (directory) { candidate = directory; candidate[len] = '/'; candidate[len + 1] = 0; add_string(out, candidate); }
                } else if (S_ISREG(st.st_mode)) add_string(out, candidate);
            }
            free(candidate);
        }
        closedir(stream);
    }
    free(typed);
}
/* Only completed words are needed here. Preserve quoted/escaped argument text. */
static void words_before(const char *line, size_t length, Strings *words) {
    char *word = malloc(length + 1);
    if (!word) return;
    size_t used = 0; int quote = 0, active = 0;
    for (size_t i = 0; i < length; i++) {
        unsigned char c = (unsigned char)line[i];
        if (c == '\\' && quote != '\'' && i + 1 < length) { word[used++] = line[++i]; active = 1; }
        else if (quote) { if (c == quote) quote = 0; else word[used++] = (char)c; active = 1; }
        else if (c == '\'' || c == '"') { quote = c; active = 1; }
        else if (isspace(c)) {
            if (active) { word[used] = 0; add_string(words, word); used = 0; active = 0; }
        } else { word[used++] = (char)c; active = 1; }
    }
    if (active) { word[used] = 0; add_string(words, word); }
    free(word);
}
static void programmable_matches(const Specification *spec, const char *text,
                                 const char *previous, const char *line, int point, Strings *out) {
    int descriptors[2];
    if (pipe(descriptors) < 0) return;
    pid_t pid = fork();
    if (pid == 0) {
        close(descriptors[0]);
        if (dup2(descriptors[1], STDOUT_FILENO) < 0) _exit(127);
        close(descriptors[1]);
        char point_text[32]; snprintf(point_text, sizeof(point_text), "%d", point);
        if (setenv("COMP_LINE", line, 1) < 0 || setenv("COMP_POINT", point_text, 1) < 0) _exit(127);
        char *args[] = {spec->script, spec->command, (char *)text, (char *)previous, NULL};
        execvp(args[0], args); _exit(127);
    }
    close(descriptors[1]);
    if (pid < 0) { close(descriptors[0]); return; }
    FILE *stream = fdopen(descriptors[0], "r");
    if (stream) {
        char *candidate = NULL; size_t allocated = 0; ssize_t length;
        while ((length = getline(&candidate, &allocated, stream)) >= 0) {
            while (length && (candidate[length - 1] == '\n' || candidate[length - 1] == '\r')) candidate[--length] = 0;
            if (length && starts_with(candidate, text)) add_string(out, candidate);
        }
        free(candidate); fclose(stream);
    } else close(descriptors[0]);
    while (waitpid(pid, NULL, 0) < 0 && errno == EINTR) {}
}
static char *next_match(const char *text, int state) {
    (void)text;
    if (!state) match_index = 0;
    return match_index < matches.count ? strdup(matches.items[match_index++]) : NULL;
}
static char **attempt_completion(const char *text, int start, int end) {
    clear_strings(&matches);
    rl_attempted_completion_over = 1;
    rl_filename_completion_desired = 0;
    rl_completion_append_character = ' ';
    /* libedit may leave stale bytes beyond rl_end, especially after UTF-8
     * input replaces a longer line. rl_end is the authoritative byte length. */
    size_t line_length = rl_end > 0 ? (size_t)rl_end : 0;
    char *line = strndup(rl_line_buffer ? rl_line_buffer : "", line_length);
    if (!line) return NULL;
    int programmed = 0;
    int libedit = rl_library_version && (strstr(rl_library_version, "EditLine") || strstr(rl_library_version, "libedit"));
    size_t before = start > 0 ? (size_t)start : 0;
    if (before > line_length) before = line_length;
    Strings words = {0}; words_before(line, before, &words);
    if (!words.count) command_matches(text, &matches);
    else {
        Specification *spec = find_specification(words.items[0]);
        if (spec) { programmed = 1; programmable_matches(spec, text, words.items[words.count - 1], line, end, &matches); }
        else file_matches(text, &matches);
    }
    clear_strings(&words); free(line); sort_unique(&matches);
    if (!matches.count && libedit) { fputc('\a', stdout); fflush(stdout); }
    if (programmed && libedit && matches.count > 1) {
        size_t common = strlen(matches.items[0]);
        for (size_t i = 1; i < matches.count; i++) {
            size_t j = 0;
            while (j < common && matches.items[i][j] == matches.items[0][j]) j++;
            common = j;
        }
        if (common > strlen(text)) {
            char *prefix = strndup(matches.items[0], common);
            if (prefix) {
                clear_strings(&matches); add_string(&matches, prefix); free(prefix);
                rl_completion_append_character = '\0';
            }
        }
    }
    if (matches.count == 1) {
        size_t n = strlen(matches.items[0]);
        if (n && matches.items[0][n - 1] == '/') rl_completion_append_character = '\0';
    }
    char **result = rl_completion_matches(text, next_match);
    rl_filename_completion_desired = 0;
    clear_strings(&matches);
    return result;
}
/* Readline's default columns pad to the longest name. The exercise expects
 * two spaces between alternatives regardless of their lengths. */
#ifndef __APPLE__
static void display_matches(char **candidates, int count, int longest) {
    (void)longest;
    putchar('\n');
    for (int i = 1; i <= count; i++) printf("%s%s", i > 1 ? "  " : "", candidates[i]);
    putchar('\n');
    rl_on_new_line();
    rl_redisplay();
}
#endif
void completion_initialize(void) {
#ifndef __APPLE__
    rl_completion_display_matches_hook = display_matches;
#endif
    rl_completer_word_break_characters = " \t\n";
    rl_attempted_completion_function = attempt_completion;
    rl_bind_key('\t', rl_complete);
}
static void print_quoted(const char *text) {
    putchar('\'');
    for (; *text; text++) { if (*text == '\'') fputs("'\\''", stdout); else putchar(*text); }
    putchar('\'');
}
int completion_builtin(int argc, char **argv) {
    if (argc > 1 && !strcmp(argv[1], "-C")) {
        if (argc < 4) { fputs("complete: -C requires a script and command\n", stderr); return 1; }
        for (int i = 3; i < argc; i++) {
            char *script = strdup(argv[2]); if (!script) return 1;
            Specification *spec = find_specification(argv[i]);
            if (spec) { free(spec->script); spec->script = script; }
            else {
                spec = calloc(1, sizeof(*spec));
                if (!spec) { free(script); return 1; }
                spec->command = strdup(argv[i]);
                if (!spec->command) { free(script); free(spec); return 1; }
                spec->script = script; spec->next = specifications; specifications = spec;
            }
        }
        return 0;
    }
    if (argc > 1 && !strcmp(argv[1], "-p")) {
        int result = 0;
        for (int i = 2; i < argc; i++) {
            Specification *spec = find_specification(argv[i]);
            if (spec) { fputs("complete -C ", stdout); print_quoted(spec->script); printf(" %s\n", spec->command); }
            else { fprintf(stderr, "complete: %s: no completion specification\n", argv[i]); result = 1; }
        }
        return result;
    }
    if (argc > 1 && !strcmp(argv[1], "-r")) {
        for (int i = 2; i < argc; i++) {
            Specification **link = &specifications;
            while (*link && strcmp((*link)->command, argv[i])) link = &(*link)->next;
            if (*link) { Specification *removed = *link; *link = removed->next; free(removed->command); free(removed->script); free(removed); }
        }
        return 0;
    }
    fputs("complete: expected -C, -p, or -r\n", stderr); return 1;
}
void completion_cleanup(void) {
    clear_strings(&matches);
    while (specifications) { Specification *next = specifications->next; free(specifications->command); free(specifications->script); free(specifications); specifications = next; }
}
