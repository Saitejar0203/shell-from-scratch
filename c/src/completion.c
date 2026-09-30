#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <dirent.h>
#include <unistd.h>
#include <sys/stat.h>
#include <readline/readline.h>
static char **candidates;
static size_t count, cursor;
static void add_candidate(const char *name, const char *prefix) {
    if (strncmp(name, prefix, strlen(prefix))) return;
    for (size_t i=0; i<count; i++) if (!strcmp(candidates[i], name)) return;
    char **next = realloc(candidates, (count+1)*sizeof(*next));
    if (!next) return;
    candidates=next; candidates[count++]=strdup(name);
}
static int compare(const void *a,const void *b) { return strcmp(*(char*const*)a,*(char*const*)b); }
static char *command_candidate(const char *text, int state) {
    if (!state) {
        for (size_t i=0;i<count;i++) free(candidates[i]);
        free(candidates); candidates=NULL; count=cursor=0;
        const char *names[]={"echo","exit","type","pwd","cd",NULL};
        for (size_t i=0;names[i];i++) add_candidate(names[i],text);
        char *paths=strdup(getenv("PATH")?getenv("PATH"):""), *walk=paths,*dir;
        while ((dir=strsep(&walk,":"))) {
            if (!*dir) dir=".";
            DIR *stream=opendir(dir); if (!stream) continue;
            struct dirent *entry;
            while ((entry=readdir(stream))) {
                size_t size=strlen(dir)+strlen(entry->d_name)+2;
                char *path=malloc(size); if (!path) continue;
                snprintf(path,size,"%s/%s",dir,entry->d_name);
                struct stat st;
                if (!stat(path,&st)&&S_ISREG(st.st_mode)&&!access(path,X_OK)) add_candidate(entry->d_name,text);
                free(path);
            }
            closedir(stream);
        }
        free(paths); qsort(candidates,count,sizeof(*candidates),compare);
    }
    return cursor<count?strdup(candidates[cursor++]):NULL;
}
static char *file_candidate(const char *text, int state) {
    char *candidate = rl_filename_completion_function(text, state);
    struct stat st;
    if (candidate && !stat(candidate, &st) && S_ISDIR(st.st_mode)) {
        size_t length = strlen(candidate);
        if (length && candidate[length-1] != '/') {
            char *directory = realloc(candidate, length+2);
            if (directory) { candidate=directory; candidate[length]='/'; candidate[length+1]=0; }
        }
        rl_completion_append_character=0;
    }
    return candidate;
}
static char **complete_word(const char *text,int start,int end) {
    (void)end; rl_attempted_completion_over=1;
    rl_completion_append_character = ' ';
    char **matches = start == 0 ? rl_completion_matches(text, command_candidate)
                                : rl_completion_matches(text, file_candidate);
    rl_filename_completion_desired = 0;
#ifdef __APPLE__
    if (!matches) { putchar('\a'); fflush(stdout); }
#endif
    return matches;
}
#ifndef __APPLE__
static void display_matches(char **matches, int count, int longest) {
    (void)longest;
    putchar('\n');
    for (int i=1; i<=count; i++) printf("%s%s", i>1?"  ":"", matches[i]);
    putchar('\n');
    rl_on_new_line(); rl_redisplay();
}
#endif
void completion_initialize(void) {
#ifndef __APPLE__
    rl_completion_display_matches_hook = display_matches;
#endif
    rl_attempted_completion_function=complete_word;
    rl_bind_key('\t',rl_complete);
}
