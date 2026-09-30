#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    setbuf(stdout, NULL);
    char *line = NULL;
    size_t capacity = 0;
    while (printf("$ "), getline(&line, &capacity, stdin) >= 0) {
        line[strcspn(line, "\r\n")] = '\0';
        if (!strcmp(line, "exit") || !strcmp(line, "exit 0")) break;
        printf("%s: command not found\n", line);
    }
    free(line);
    return 0;
}
