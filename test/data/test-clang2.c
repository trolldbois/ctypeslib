#include <stdint.h>
//#include <inttypes.h>

typedef struct Anon;
//struct Anon2;

int a = 2;
int b = a; // ERROR
char c = 'x';
char d = '1';
char e[] = "abcde";
float f = 2.1;
double g = 2.2;
long double h = 2.3;

long long int i1 = 0x7FFFFFFFFFFFFFFFLL;
float i2 = 2.2f;
