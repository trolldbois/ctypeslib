


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

// case 3 bytes bitfield
struct bytes3 { // should be 8 bytes
    unsigned int a1; // 0-31
    unsigned int b1:23; // 32-55 
    char a2; // 56-64 but python says 64-72
};

// case 3 bytes bitfield
struct bytes3b { // should be 8 bytes
    unsigned int b1:23; // 32-55 
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



/*
// more complex
struct complex {
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
*/
