#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>

// classes
class cA {
  private:
    int _m1;
    char _x;
  public:
    int a;
    char p[5];
  //cA() : a(0x1){  };
  cA(int _a=42, int _m=0) { 
    this->_x = 'X'; 
    this->setM(_m);
    char * s = (char*)malloc(5);
    strcpy(s,"PLOP");
    strcpy(this->p,s);
  };
  void setM(int m){
    this->_m1 = m;
    this->a = 42+m; // 1
  };
};

class cB : cA {
  public:
  unsigned int b;
  cB(int _b=0x22) : b(_b) { cA(0x2);};
};


// Standard Template Library example
#include <iostream>
#include <list>
#include <vector>
using namespace std;

// Simple example uses type int

/*
class struct_88a11f8(LoadableMembers):  # resolved:True SIG:P4P4i4 pointerResolved:True
  _fields_ = [ 
	( 'ptr_struct_88a1208' , ctypes.POINTER(struct_88a1208) ), # @ 88a1208 [heap] 
	( 'ptr_struct_88a11e8' , ctypes.POINTER(struct_88a11e8) ), # @ 88a11e8 [heap] 
	( 'small_int_8' , ctypes.c_uint ), #  18  
 ]
*/
void make_list_int()
{
  list<int> * L = new list<int>;
  for (int i=10; i<20; i++) {
    L->push_back(i);
  }
  
  printf("ADDR: list_int %d %d 10 elements \n", (unsigned int) L, sizeof(int));
  fflush(stdout);  
  return;
}

/*
class struct_88a1278(LoadableMembers):  # resolved:True SIG:P4P4i4P4i4I4P4 pointerResolved:False
  _fields_ = [ 
	( 'ptr_struct_88a1298' , ctypes.POINTER(struct_88a1298) ), # @ 88a1298 [heap] 
	( 'ptr_struct_88a1258' , ctypes.POINTER(struct_88a1258) ), # @ 88a1258 [heap] 
	( 'small_int_8' , ctypes.c_uint ), #  22  
	( 'ptr_ext_lib_12' , ctypes.c_void_p ), # @ 8048958 /home/jal/Compil/python-haystack/test/src/test-ctypes4  // .data not copied.
	( 'small_int_16' , ctypes.c_uint ), #  43  
	( 'int_20' , ctypes.c_uint ), #  1347374160   // ptr to PLOP in .DATA ?
	( 'ptr_24' , ctypes.c_void_p ), # @ 88a1100 [heap]  // ???
 ]
*/  
void make_list_obj()
{
  list<cA> * L = new list<cA>;
  cA a = cA(42, 0);
  for (int i=20; i<30; i++) {
    //cA * a = new cA(42+i, i);
    a.setM(i);
    L->push_back(a);  
  }

  printf("ADDR: list_obj %d %d 10 elements\n", (unsigned int) L, sizeof(cA));
  fflush(stdout);  
  return;
}

/*
class struct_88a13c0(LoadableMembers):  # resolved:True SIG:i4i4i4i4i4i4i4i4i4
  _fields_ = [ 
	( 'small_int_0' , ctypes.c_uint ), #  0  
	( 'small_int_4' , ctypes.c_uint ), #  31  
	( 'small_int_8' , ctypes.c_uint ), #  32  
	( 'small_int_12' , ctypes.c_uint ), #  33  
	( 'small_int_16' , ctypes.c_uint ), #  34  
	( 'small_int_20' , ctypes.c_uint ), #  35  
	( 'small_int_24' , ctypes.c_uint ), #  36  
	( 'small_int_28' , ctypes.c_uint ), #  37  
	( 'small_int_32' , ctypes.c_uint ), #  0  
 ]
*/
void make_vector_int()
{
  vector<int> * L = new vector<int>;
  for (int i=30; i<40; i++) {
    L->push_back(i);
  }
  printf("ADDR: vector_int %d %d 10 elements \n", (unsigned int) L, sizeof(int));
  fflush(stdout);  
  return;
} 

/*
head :
class struct_88a1398(LoadableMembers):  # resolved:True SIG:P4P4P4 pointerResolved:False
  _fields_ = [ 
	( 'ptr_struct_88a1560' , ctypes.POINTER(struct_88a1560) ), # @ 88a1560 [heap] 
	( 'zerroes_ptr_struct_88a1560_field_zerroes_200' , ctypes.POINTER(ctypes.c_ubyte) ), # @ 88a1628 [heap] 
	( 'ptr_8' , ctypes.c_void_p ), # @ 88a16a0 [heap] 
 ]


class struct_88a1148(LoadableMembers):  # resolved:True SIG:P4P4i4i4i4T5u3 pointerResolved:True
  _fields_ = [ 
	( 'ptr_struct_88a1008' , ctypes.POINTER(struct_88a1008) ), # @ 88a1008 [heap] 
	( 'ptr_struct_88a1128' , ctypes.POINTER(struct_88a1128) ), # @ 88a1128 [heap] 
	( 'small_int_8' , ctypes.c_uint ), #  49  
	( 'small_int_12' , ctypes.c_uint ), #  88  
	( 'small_int_16' , ctypes.c_uint ), #  43  
	( 'text_20' , ctypes.c_char * 5 ), #    u'PLOP\x00'
	( 'untyped_25' , ctypes.c_ubyte * 3 ), #   else bytes:'T\\\xb7'
 ]
*/
void make_vector_obj()
{
  vector<cA> * L = new vector<cA>;
  cA a = cA(42, 0);
  for (int i=40; i<50; i++) {
    a.setM(i);
    L->push_back(a);  
  }
  printf("ADDR: vector_obj %d %d 10 elements\n", (unsigned int) L, sizeof(cA));
  fflush(stdout);  
  return;
}

void idheap(){
  list<cA> * L = new list<cA>;
  cA a = cA(42, 0);
  for (int i=40; i<50; i++) {
    a.setM(i);
    L->push_back(a);  
  }
  printf("ADDR: vector_obj %d %d 10 elements\n", (unsigned int) L, sizeof(cA));
  fflush(stdout);  
  return;
}


int main(){
  int a;

  printf("START %d\n",getpid());
  fflush(stdout);
  
  idheap();
  make_list_int();
  make_list_obj();
  make_vector_int();
  make_vector_obj();

  a = getchar();
  printf("END\n");
  fflush(stdout);
  return 0;
}
