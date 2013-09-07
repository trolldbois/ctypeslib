struct s0
{
  unsigned int val1;
  unsigned int val2;
  unsigned int * me;
  unsigned int val2b;
  unsigned long val1b;
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
  union u1 val2;
};

union u2 { 
  struct s1 val1;
  union u1 val2;
};

union invalid1 {
  struct s1 val1;
  union u1 val2;
}

int main(){
  return 0;
}


