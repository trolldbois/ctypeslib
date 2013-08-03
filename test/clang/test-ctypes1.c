
#ifdef PYTHON_BUILD
#define __cplusplus

#define new new_
#define private private_

#define SHARED
    struct auditstate
    {
      __uint32_t * cookie;
      __uint32_t bindflags;
    };
#endif

#ifdef SHARED
int shared_activated_start = 0;
#endif


#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <dlfcn.h>
#include <stdbool.h>

//#include "ldsodefs.h"

//#undef _dl_mcount_wrapper_check

//extern struct rtld_global _rtld_local;
#ifndef PYTHON_BUILD
extern struct rtld_global _rtld_global;
extern struct rtld_global_ro _rtld_global_ro;
#endif

// TEST ZONE

struct Node {
  unsigned int val1;
  void * ptr2;
};


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
  //int (*sym) (void); 
  //Dl_info info;
  //int ret;
  
  
  #ifdef __USE_GNU
  printf("__USE_GNU\n");
  #endif

  handle = (void *)1;
  //handle = dlopen ("libQtCore.so", RTLD_NOW|RTLD_GLOBAL);
  //handle = dlopen ("libQtGui.so", RTLD_NOW|RTLD_GLOBAL);
  handle = dlopen ("libQtNetwork.so", RTLD_NOW|RTLD_GLOBAL);
  //handle = dlopen ("libQtSvg.so", RTLD_NOW|RTLD_GLOBAL);
  if (handle == NULL){
    fprintf (stderr, "cannot load: lib.so\n");
    return -1;  
  }
  
  printf("_rtld_global 0x%lx\n",(unsigned long )&_rtld_global);
  //printf("_rtld_global._dl_initfirst 0x%x\n",(&_rtld_global) + offsetof(struct rtld_global, _dl_initfirst) );
  
  //printf("_rtld_local 0x%x\n",(unsigned int )&_rtld_local);
  printf("_rtld_global_ro 0x%lx\n",(unsigned long )&_rtld_global_ro);
 
  // TEST
  test1();
  
  printf("pid %d\n",getpid());
  fflush(stdout);
  sleep(-1);
  
  return 0;
}

#ifdef SHARED
int shared_activated_end = 0;
#endif


