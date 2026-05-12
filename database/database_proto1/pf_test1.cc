#include <cstdio>
#include <iostream>
#include <cstring>
#include <unistd.h>
#include "pf.h"
#include "pf_internal.h"
#include "pf_hashtable.h"

using namespace std;

#define FILE1 "file1"
#define FILE2 "file2"

RC WriteFile(PF_Manager &pfm, char *fname);
RC PrintFile(PF_FileHandle &fh);
RC ReadFile(PF_Manager &pfm, char *fname);
RC TestPF();
RC TestHash();

int main() {
    return 0;
}