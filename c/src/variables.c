#include "variables.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct Variable {
    char *name;
    char *value;
    struct Variable *next;
} Variable;

static Variable *variables;

static Variable *find_variable(const char *name) {
    for (Variable *v = variables; v; v = v->next)
        if (!strcmp(v->name, name)) return v;
    return NULL;
}

static int initial_character(unsigned char c) {
    return c == '_' || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
}

static int valid_name(const char *text, size_t length) {
    if (!length || !initial_character((unsigned char)text[0])) return 0;
    for (size_t i = 1; i < length; i++) {
        unsigned char c = (unsigned char)text[i];
        if (!initial_character(c) && !(c >= '0' && c <= '9')) return 0;
    }
    return 1;
}

const char *variable_get(const char *name) {
    Variable *v = find_variable(name);
    return v ? v->value : "";
}

static void print_variable(const Variable *v) {
    printf("declare -- %s=\"", v->name);
    for (const unsigned char *p = (const unsigned char *)v->value; *p; p++) {
        if (*p == '\\' || *p == '"' || *p == '$' || *p == '`') putchar('\\');
        putchar(*p);
    }
    puts("\"");
}

int variables_builtin(int argc, char **argv) {
    int status = 0;
    if (argc > 1 && !strcmp(argv[1], "-p")) {
        for (int i = 2; i < argc; i++) {
            Variable *v = find_variable(argv[i]);
            if (v) print_variable(v);
            else { fprintf(stderr, "declare: %s: not found\n", argv[i]); status = 1; }
        }
        return status;
    }
    for (int i = 1; i < argc; i++) {
        const char *equal = strchr(argv[i], '=');
        size_t length = equal ? (size_t)(equal - argv[i]) : strlen(argv[i]);
        if (!valid_name(argv[i], length)) {
            fprintf(stderr, "declare: `%s': not a valid identifier\n", argv[i]);
            status = 1;
            continue;
        }
        char *name = malloc(length + 1);
        if (!name) { perror("declare"); return 1; }
        memcpy(name, argv[i], length); name[length] = 0;
        Variable *v = find_variable(name);
        if (v && !equal) { free(name); continue; }
        char *value = strdup(equal ? equal + 1 : "");
        if (!value) { free(name); perror("declare"); return 1; }
        if (v) {
            free(name); free(v->value); v->value = value;
        } else {
            v = malloc(sizeof(*v));
            if (!v) { free(name); free(value); perror("declare"); return 1; }
            *v = (Variable){name, value, variables}; variables = v;
        }
    }
    return status;
}

void variables_clear(void) {
    while (variables) {
        Variable *next = variables->next;
        free(variables->name); free(variables->value); free(variables);
        variables = next;
    }
}
