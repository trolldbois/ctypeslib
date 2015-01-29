

struct Name
{
  short member1;
  int member2;
  unsigned int member3;
  unsigned int member4;
  unsigned int member5;
} __attribute__((packed));

struct Name2
{
  short member1;
  int member2;
  unsigned int member3;
  unsigned int member4;
  unsigned int member5;
};

struct Node {
  unsigned int val1;
  void * ptr2;
  int * ptr3;
  struct Node2 * ptr4;
};

struct Node2 {
  unsigned char m1;
  struct Node * m2;
};

enum myEnum {
ONE,
TWO,
FOUR = 4 
};

typedef struct
{
  long __val[2];
} my__quad_t;

typedef struct
{
  long a:3;
  long b:4;
  unsigned long long c:3;
  unsigned long long d:3;
  long f:2;
} my_bitfield;

typedef struct __attribute__((packed)) {
    int a;
    char c;
} mystruct;

struct Anon;
struct Anon2;

/* sudo apt-get install libc6-dev-i386  */
/*
#include <stdio.h>

void main() {
printf("struct Name:  %d\n",sizeof(struct Name));
printf("struct Name2: %d\n",sizeof(struct Name2));
printf("struct Node:  %d\n",sizeof(struct Node));
printf("struct Node2: %d\n",sizeof(struct Node2));
printf("myEnum:       %d\n",sizeof(ONE));
printf("my__quad_t:   %d\n",sizeof(my__quad_t));
printf("my_bitfield:  %d\n",sizeof(my_bitfield));
printf("mystruct:     %d\n",sizeof(mystruct));
//printf("struct Anon:     %d\n",sizeof(struct Anon));
}
*/
