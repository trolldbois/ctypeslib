#define MY_VAL 1
#define __MY_VAL 1

#define plop void

#define example(a,b) {a,b}

#define x(c,d) plopi(c,d)


plop x(int f, int g);

#define PRE "before"
#define POST " after"
#define PREPOST PRE POST

char c1[] = "what";
char c2[] = "why" " though";
char c3[] = PRE POST;
char c4[] = PREPOST;

int i = MY_VAL;