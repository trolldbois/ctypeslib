/* pointer tests */


struct Node {
  unsigned char m1;
};

struct Node2 {
  struct Node * ptr1;
  unsigned char * ptr2;
  unsigned short * ptr3;
  unsigned int * ptr4;
  unsigned long * ptr5;
  unsigned long long * ptr6;
  double * ptr7;
  long double * ptr8;
  void * ptr9;
};

struct Node3 {
  struct Node f1;
  unsigned char f2;
  unsigned short f3;
  unsigned int f4;
  unsigned long f5;
  unsigned long long f6;
  double f7;
  long double f8;
};

