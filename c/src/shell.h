#ifndef SHELL_H
#define SHELL_H
#include <stddef.h>
typedef struct { char **words; size_t count; } Words;
void *allocate(size_t bytes);
Words parse(const char *line);
void free_words(Words words);
#endif
