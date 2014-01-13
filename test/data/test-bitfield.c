

// case 4 bytes on int32
struct bytes4 {
    unsigned int a1;
    unsigned int b1:9;
    unsigned int c1:9;
    unsigned int d1:9;
    char a2;
};



// case 4 bytes on int32
struct bytes4b {
    unsigned int b1:9;
    unsigned int c1:9;
    unsigned int d1:9;
};


//  3 bytes bitfield +1 char packed into a int32
// packed on 4 bytes by compiler. But ctypes cannot put b1 in 3 bytes type
// so we force a2 in the bitfield
struct bytes3 { // should be 8 bytes
    unsigned int a1; // 0-31
    unsigned int b1:23; // 32-55 
    char a2; // 56-64 but python says 64-72
};


// case 3 bytes bitfield
struct bytes3b { // should be 8 bytes
    unsigned int b1:23; // 32-55 
};

// that works because a2 cant align in bitfield
struct bytes3c { 
    unsigned int b1:23; // 0-23
    // 9 bit align
    short a2; // 32-48 + pad
};


// case 2 bytes on int32
struct bytes2 {
    unsigned int a1;
    unsigned int b1:4;
    unsigned int c1:5;
    unsigned int d1:5;
    char a2;
};

// case 2 bytes on int32
struct bytes2b {
    unsigned int b1:4;
    unsigned int c1:5;
    unsigned int d1:5;
};

// case 1 byte on int32
struct byte1 {
    unsigned int b1:4;
    char a2;
};



// case 1 byte on int32
struct byte1b {
    unsigned int b1:4;
};


struct complex1 {
    unsigned char a1:1;
    unsigned char b1:7;
    unsigned int c1:1;
    unsigned int d1:31;
};


/*

class struct_complex(ctypes.Structure):
    _pack_ = True # source:False
    _fields_ = [
    ('a1', ctypes.c_uint32),
    ('b1', ctypes.c_uint16, 4),
    ('c1', ctypes.c_uint16, 10),
    ('d1', ctypes.c_uint16, 2),
    ('a2', ctypes.c_byte),
    ('b2', ctypes.c_uint8, 4),
    ('PADDING_0', ctypes.c_uint8, 4),
    ('c2', ctypes.c_uint32, 10),
    ('d2', ctypes.c_uint32, 2),
    ('PADDING_1', ctypes.c_uint32, 20),
    ('h', ctypes.c_int32),
     ]


class struct_complex(ctypes.Structure):
    _pack_ = True # source:False
    _fields_ = [
    ('a1', ctypes.c_uint32),
    ('b1', ctypes.c_uint16, 4),
    ('c1', ctypes.c_uint16, 10),
    ('d1', ctypes.c_uint16, 2),
    ('a2', ctypes.c_byte),
    ('b2', ctypes.c_uint8, 4),
    ('PADDING_0', ctypes.c_uint8, 4),
    ('c2', ctypes.c_uint16, 10),
    ('d2', ctypes.c_uint32, 2),
    ('PADDING_1', ctypes.c_uint32, 20),
    ('h', ctypes.c_int32),
     ]
     
DEBUG:cursorhandler:Struct/Union_FIX: struct_complex 
DEBUG:cursorhandler:Fixup_struct: Member:a1 offsetbits:0->32 expecting offset:0
DEBUG:cursorhandler:Fixup_struct: Member:b1 offsetbits:32->36 expecting offset:32
DEBUG:cursorhandler:Fixup_struct: Member:c1 offsetbits:36->46 expecting offset:36
DEBUG:cursorhandler:Fixup_struct: Member:d1 offsetbits:46->48 expecting offset:46
DEBUG:cursorhandler:Fixup_struct: Member:a2 offsetbits:48->56 expecting offset:48

DEBUG:cursorhandler:Fixup_struct: Member:b2 offsetbits:56->60 expecting offset:56
padding_0
DEBUG:cursorhandler:Fixup_struct: Member:c2 offsetbits:64->74 expecting offset:60
DEBUG:cursorhandler:Fixup_struct: Member:d2 offsetbits:74->76 expecting offset:74
paddin_1 20 bits

DEBUG:cursorhandler:Fixup_struct: Member:h offsetbits:96->128 expecting offset:76
DEBUG:cursorhandler:Fixup_struct: create padding for 20 bits 2 bytes
DEBUG:cursorhandler:_make_padding: for 20 bits
DEBUG:cursorhandler:FIXUP_STRUCT: size:128 offset:128
DEBUG:cursorhandler:_fixup_record_bitfield_size: fix type to c_uint16
DEBUG:cursorhandler:_fixup_record_bitfield_size: fix type to c_uint8
DEBUG:cursorhandler:_fixup_record_bitfield_size: fix type to c_uint32


size of type
closure of bitfield
*/
struct complex {
    unsigned int a1;
    unsigned int b1:4;
    unsigned int c1:10;
    unsigned int d1:2;
    char a2;
    unsigned int b2:4;
    unsigned int c2:10;
    unsigned long long d2:2;
    int h;
};



struct complex2 {
    unsigned int a1;
    unsigned int b1:4;
    unsigned int c1:10;
    unsigned int d1:2;
    char a2;
    unsigned int b2:4;
    unsigned int c2:10;
    unsigned long long d2:3;
    int h;
};

