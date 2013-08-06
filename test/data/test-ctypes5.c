#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

typedef struct entry Entry;

struct entry {
  Entry * flink;
  Entry * blink;
};


struct usual
{
  unsigned int val1;
  unsigned int val2;
  Entry root;
  unsigned int val2b;
  unsigned int val1b;
};

struct Node
{
  unsigned int val1;
  Entry list;
  unsigned int val2;
};



int test1(){

  struct usual * usual;
  usual = (struct usual *) malloc(sizeof(struct usual));

  struct Node * node1;
  struct Node * node2;
  node1 = (struct Node *) malloc(sizeof(struct Node));
  node1->val1 = 0xdeadbeef;
  node1->val2 = 0xffffffff;
  node2 = (struct Node *) malloc(sizeof(struct Node));
  node2->val1 = 0xdeadbabe;
  node2->val2 = 0xffffffff;

  node1->list.flink = &node2->list;
  node1->list.blink = (struct entry *) 0;

  node2->list.flink = (struct entry *) 0;
  node2->list.blink = &node1->list;

  usual->root.flink = &node1->list;
  usual->root.blink = &node1->list;

  printf("test1 0x%lx\n",(unsigned long )usual);
  
  return 0;
}


int main(){


  test1();
  
  printf("pid %d\n",getpid());
  fflush(stdout);
  sleep(-1);
  
  return 0;
}


