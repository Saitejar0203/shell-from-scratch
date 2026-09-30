#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    setbuf(stdout, NULL);
    printf("$ ");
    char *line = NULL;
    size_t capacity = 0;
    if (getline(&line, &capacity, stdin) >= 0) {
        line[strcspn(line, "\r\n")] = '\0';
        printf("%s: command not found\n", line);
    }
    free(line);
    return 0;
}
