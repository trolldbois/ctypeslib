struct test0
{
  unsigned int val1;
  unsigned int val2;
  unsigned int * me;
  unsigned int val2b;
  unsigned int val1b;
};

struct s1 {
  unsigned int val1;
  void * ptr2;
};

union u1 {
  unsigned int val1;
  void * ptr2;
};

struct s2 {
  struct s1 val1;
  union u1 val1;
}

union u2 {
  struct s1 val1;
  union u1 val1;
}

int main(){
  return 0;
}


