#ifndef PF_HASHTABLE_H
#define PF_HASHTABLE_H

#include "pf_internal.h"

struct PF_HashEntry {
    PF_HashEntry *next;
    PF_HashEntry *prev;
    int          fd;
    PageNum      pageNum;
    int          slot;
};

class PF_HashTable {
public:
    PF_HashTable(int numBuckets);
    ~PF_HashTable();
    int Find(int fd, PageNum pageNum, int &slot);
    RC Insert(int fd, PageNum pageNum, int slot);
    RC Delete(int fd, PageNum pageNum);

private:
    int Hash(int fd, PageNum pageNum) const {
        return ((fd + pageNum) % numBuckets);
    }
    int numBuckets;
    PF_HashEntry **hashTable;
};

#endif