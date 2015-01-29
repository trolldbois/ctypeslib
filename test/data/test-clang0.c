/** very simple tests */
typedef struct
{
  long __val[2];
} my__quad_t;

typedef int badaboum;
typedef unsigned int you_badaboum;
typedef long big_badaboum;
typedef unsigned long you_big_badaboum;
typedef double double_badaboum;
typedef long double long_double_badaboum;
typedef float float_badaboum;
typedef void* ptr;

/* sudo apt-get install libc6-dev-i386  */
/*
#include <stdio.h>

void main() {
printf("my__quad_t:   %d\n",sizeof(my__quad_t));
printf("int badaboum:  %d\n",sizeof(badaboum));
printf("you_badaboum: %d\n",sizeof(you_badaboum));
printf("you_big_badaboum:  %d\n",sizeof(you_big_badaboum));
printf("double_badaboum: %d\n",sizeof(double_badaboum));
printf("long_double_badaboum:       %d\n",sizeof(long_double_badaboum));
printf("float_badaboum:  %d\n",sizeof(float_badaboum));
printf("ptr:     %d\n",sizeof(ptr));
}
*/
