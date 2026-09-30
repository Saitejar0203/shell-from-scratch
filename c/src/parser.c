#include "shell.h"
#include "variables.h"
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
void *allocate(size_t bytes) {
    void *p = malloc(bytes);
    if (!p) { perror("malloc"); exit(1); }
    return p;
}
static int name_start(unsigned char c) {
    return c=='_' || (c>='a' && c<='z') || (c>='A' && c<='Z');
}
static int name_part(unsigned char c) { return name_start(c) || (c>='0' && c<='9'); }
Words parse(const char *line) {
    size_t n = strlen(line), pos = 0;
    Words result = {allocate((n + 1) * sizeof(char *)), allocate(n + 1), 0};
    while (line[pos]) {
        if (isspace((unsigned char)line[pos])) { pos++; continue; }
        if (line[pos] == '|') {
            result.words[result.count] = strdup("|");
            result.operators[result.count++] = 3; pos++; continue;
        }
        if (line[pos] == '&') {
            result.words[result.count] = strdup("&");
            result.operators[result.count++] = 2; pos++; continue;
        }
        if (line[pos] == '>' || ((line[pos] == '1' || line[pos] == '2') && line[pos+1] == '>')) {
            size_t begin = pos;
            if (line[pos] == '1' || line[pos] == '2') pos++;
            pos++;
            if (line[pos] == '>') pos++;
            result.words[result.count] = strndup(line + begin, pos - begin);
            result.operators[result.count++] = 1;
            continue;
        }
        char *word = allocate(n + 1); size_t used = 0, room = n+1; int quote = 0;
        while (line[pos]) {
            char c = line[pos];
            if (!quote && (isspace((unsigned char)c) || c == '>' || c == '&' || c == '|')) break;
            if (!quote && (c == '\'' || c == '"')) { quote = c; pos++; continue; }
            if (quote && c == quote) { quote = 0; pos++; continue; }
            if (c == '\\' && line[pos + 1] && (!quote ||
                (quote == '"' && strchr("\\\"$`\n", line[pos + 1])))) {
                pos++; word[used++] = line[pos++]; continue;
            }
            if (c=='$' && quote!='\'' && (name_start((unsigned char)line[pos+1]) || line[pos+1]=='{')) {
                size_t begin=pos+1, end=begin;
                int braces=line[begin]=='{';
                if (braces) {
                    begin++; end=begin;
                    while (line[end] && line[end]!='}') end++;
                    if (!line[end]) { word[used++]=c; pos++; continue; }
                } else while (name_part((unsigned char)line[end])) end++;
                char *name=strndup(line+begin,end-begin);
                pos=end+(braces ? 1 : 0);
                const char *value=variable_get(name);
                size_t length=strlen(value);
                room += length;
                char *grown=realloc(word,room);
                if (!grown) { perror("realloc"); exit(1); }
                word=grown;
                memcpy(word+used,value,length); used+=length;
                free(name); continue;
            }
            word[used++] = c; pos++;
        }
        word[used] = 0;
        result.operators[result.count] = 0;
        result.words[result.count++] = word;
    }
    result.words[result.count] = NULL;
    return result;
}
void free_words(Words words) {
    for (size_t i = 0; i < words.count; i++) free(words.words[i]);
    free(words.words); free(words.operators);
}
