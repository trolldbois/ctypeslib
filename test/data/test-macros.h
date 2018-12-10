#define MY_VAL 1
#define __MY_VAL 1

#define plop void

#define x(a,b) plopi(a,1,b)


plop x(int a, int b);

#define PRE "before"
#define POST " after"
#define PREPOST PRE POST

char a[] = "what";
char b[] = "why" " though";
char c[] = PRE POST;
char d[] = PREPOST;

int i = MY_VAL;