
#include <stdio.h>
#include <stdlib.h>
#include <iostream>

extern "C" {
#include <dlfcn.h>

}
#ifdef PYTHON_BUILD
#endif

// structs
struct sA {
  int a;
};

struct sB : sA {
  unsigned int b;
};

struct sC : sB {
  private:
  unsigned int c;
};

struct sD : sB {
  public:
  unsigned int d;
};

// classes
class cA {
  public:
  int a;
  //cA() : a(0x1){  };
  cA(int _a=0x1) : a(_a){  };
  
};

class cB : cA {
  public:
  unsigned int b;
  cB(int _b=0x22) : b(_b) { cA(0x2);};
};

class cC : cB {
  public:
  unsigned int c;
  cC(int _c=0x333) : c(_c) {cB(0x3);};
};

class cD : cB {
  public:
  unsigned int d;
  cD(int _d=0x4) : d(_d) {cB(0x4);};
};

class cE : cD, cC {
  public:
  unsigned int e;
  cE() : e(0x5) {cD(0x5);};
};


int test_classes()
{
  std::cout << " -- classes --" << std::endl;

  cA * a = new cA();
  cB * b = new cB();
  cC * c = new cC();
  cD * d = new cD();
  cE * e = new cE();
  
  //a->a = 0x01 ;
  //b->a = 0x02;
  //b->b = 0x22;
  //c->a = 0x03;
  //c->b = 0x33;
  //c->c = 0x0333;
  
  printf(" a is at 0x%lx size: %d \n", (unsigned long )a, sizeof(cA));
  printf(" b is at 0x%lx size: %d \n", (unsigned long )b, sizeof(cB));
  printf(" c is at 0x%lx size: %d \n", (unsigned long )c, sizeof(cC));
  printf(" d is at 0x%lx size: %d \n", (unsigned long )d, sizeof(cD));
  printf(" e is at 0x%lx size: %d \n", (unsigned long )e, sizeof(cE));

  std::cout << " -- end classes --" << std::endl;
  
  return 0;
}

int test_structs()
{
  std::cout << " -- structs --" << std::endl;

  sA * a = (sA * ) malloc(sizeof(sA));
  sB * b = (sB * ) malloc(sizeof(sB));
  sC * c = (sC * ) malloc(sizeof(sC));
  sD * d = (sD * ) malloc(sizeof(sD));

  printf(" a is at 0x%lx size: %d \n", (unsigned long )a, sizeof(sA));
  printf(" b is at 0x%lx size: %d \n", (unsigned long )b, sizeof(sB));
  printf(" c is at 0x%lx size: %d \n", (unsigned long )c, sizeof(sC));
  printf(" d is at 0x%lx size: %d \n", (unsigned long )d, sizeof(sD));

  std::cout << " -- end structs --" << std::endl;
  
  return 0;
}

int main(){
  int a;
  void *handle;

  printf("START\n");

  fflush(stdout);
  //test_structs();
  //test_classes();   
  a = getchar();
  handle = dlopen ("libQtCore.so", RTLD_NOW|RTLD_GLOBAL);
  printf("OPEN libQtCore.so\n");
  fflush(stdout);
  if (handle == NULL){
    fprintf (stderr, "cannot load: lib.so\n");
    return -1;  
  }
  
  //test_structs();
  //test_classes();   
  a = getchar();
  handle = dlopen ("libQtSvg.so", RTLD_NOW|RTLD_GLOBAL);
  printf("OPEN libQtSvg.so\n");
  fflush(stdout);
  if (handle == NULL){
    fprintf (stderr, "cannot load: lib.so\n");
    return -1;  
  }
  
  //test_structs();
  //test_classes();   
  a = getchar();
  handle = dlopen ("libQtGui.so", RTLD_NOW|RTLD_GLOBAL);
  printf("OPEN libQtGui.so\n");
  fflush(stdout);
  if (handle == NULL){
    fprintf (stderr, "cannot load: lib.so\n");
    return -1;  
  }

  a = getchar();
  printf("END\n");
  fflush(stdout);
  return 0;
}
