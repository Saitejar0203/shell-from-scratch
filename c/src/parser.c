#include "shell.h"
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
void *allocate(size_t bytes) {
    void *p = malloc(bytes);
    if (!p) { perror("malloc"); exit(1); }
    return p;
}
Words parse(const char *line) {
    size_t n = strlen(line), pos = 0;
    Words result = {allocate((n + 1) * sizeof(char *)), 0};
    while (line[pos]) {
        if (isspace((unsigned char)line[pos])) { pos++; continue; }
        char *word = allocate(n + 1); size_t used = 0; int quote = 0;
        while (line[pos]) {
            char c = line[pos];
            if (!quote && isspace((unsigned char)c)) break;
            if (!quote && (c == '\'' || c == '"')) { quote = c; pos++; continue; }
            if (quote && c == quote) { quote = 0; pos++; continue; }
            if (!quote && c == '\\' && line[pos + 1]) {
                pos++; word[used++] = line[pos++]; continue;
            }
            word[used++] = c; pos++;
        }
        word[used] = 0;
        result.words[result.count++] = word;
    }
    result.words[result.count] = NULL;
    return result;
}
void free_words(Words words) {
    for (size_t i = 0; i < words.count; i++) free(words.words[i]);
    free(words.words);
}
