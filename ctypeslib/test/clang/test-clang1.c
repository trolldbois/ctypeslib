
#include <inttypes.h>

struct structName
{
  int16_t member1;
  int32_t member2;
  uint32_t member3;
  uint32_t member4;
  uint32_t member5;
}; /*__attribute__((packed));*/

struct structName2
{
  int16_t member1;
  int32_t member2;
  uint32_t member3;
  uint32_t member4;
  uint32_t member5;
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
  uint64_t c:3;
  uint64_t d:3;
  long f:2;
} my_bitfield;

//COREDUMP 
//struct Anon;
//struct Anon2;

