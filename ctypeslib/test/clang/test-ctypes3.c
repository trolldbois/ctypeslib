#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <dlfcn.h>
#include <stdbool.h>

struct test3
{
  unsigned int val1;
  unsigned int val2;
  unsigned int * me;
  unsigned int val2b;
  unsigned int val1b;
};

struct Node {
  unsigned int val1;
  void * ptr2;
};

int test3(){
  struct test3 * t3;
  t3 = (struct test3 *) malloc(sizeof(struct test3));
  t3->val1 = 0xdeadbeef;
  t3->val1b = 0xdeadbeef;
  t3->val2 = 0x10101010;
  t3->val2b = 0x10101010;
  t3->me = (unsigned int *) t3;
  printf("test3 0x%lx\n",(unsigned long )t3);
  
  return 0;
}

int test1(){
  struct Node * node;
  node = (struct Node *) malloc(sizeof(struct Node));
  node->val1 = 0xdeadbeef;
  node->ptr2 = node;
  printf("test1 0x%lx\n",(unsigned long )node);
  
  return 0;
}


int main(){

  void *handle;
  // TEST
  test1();
  test3();
  test1();
  test3();
  test1();
  test3();
  
  printf("pid %d\n",getpid());
  fflush(stdout);
  sleep(-1);
  
  return 0;
}


