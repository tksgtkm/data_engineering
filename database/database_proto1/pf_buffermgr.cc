#include <cstdio>
#include <unistd.h>
#include <iostream>

#include "pf_buffermgr.h"

#ifdef PF_LOG

void WriteLog(const char *psMessage) {
    static FILE *fLog = nullptr;

    if (fLog == nullptr) {
        int iLogNum = -1;
        int bFound = FALSE;
        char psFileName[10];

        while (iLogNum < 999 && bFound == FALSE) {
            iLogNum++;
            sprintf(psFileName, "PF_LOG.%d", iLogNum);
            fLog = fopen(psFileName, "r");
            if (fLog == nullptr) {
                bFound = TRUE;
                fLog = fopen(psFileName, "w");
            } else {
                delete fLog;
            }
        }

        if (!bFound) {
            std::cerr << "Cannot create a new log file\n";
            exit(1);
        }
    }
    fprintf(fLog, psMessage);
}

#endif

PF_BufferMgr::PF_BufferMgr(int _numPages) : hashTable(PF_HASH_TBL_SIZE) {
    this->numPages = _numPages;
    pageSize = PF_PAGE_SIZE  + sizeof(PF_PageHdr);

#ifdef PF_LOG
    char psMessage[100];
    sprintf(psMessage, "Creating buffer manager. %d pages of size %d\n",
    numPages, PF_PAGE_SIZE + sizeof(PF_PageHdr));
    WriteLog(psMessage);
#endif

    bufTable = new PF_BufPageDesc[numPages];

    for (int i = 0; i < numPages; i++) {
        if ((bufTable[i].pData = new char[pageSize]) == nullptr) {
            std::cerr << "Not enough memory for buffer\n";
            exit(1);
        }

        memset((void *)bufTable[i].pData, 0, pageSize);

        bufTable[i].prev = i - 1;
        bufTable[i].next = i + 1;
    }
    bufTable[0].prev = bufTable[numPages - 1].next = INVALID_SLOT;
    free = 0;
    first = last = INVALID_SLOT;

#ifdef PF_LOG
    WriteLog("Succesfully created the buffer manager\n");
#endif
}

PF_BufferMgr::~PF_BufferMgr() {
    for (int i = 0; i < this->numPages; i++)
        delete [] bufTable[i].pData;
    
    delete [] bufTable;

#ifdef PF_LOG
    WriteLog("Destroyed the buffer manager.\n");
#endif
}

RC PF_BufferMgr::GetPage(int fd, PageNum pageNum, char **ppBuffer, int bMultiplePins) {
    RC rc;
    int slot;

#ifdef PF_LOG
    char psMessage[100];
    sprintf(psMessage, "Lokking for (%d,%d).\n", fd, pageNum);
    WriteLog(psMessage);
#endif

    if ((rc = hashTable.Find(fd, pageNum, slot)) && (rc != PF_HASHNOTFOUND))
        return rc;
    
    if (rc == PF_HASHNOTFOUND) {
        if ((rc == InternalAlloc(slot)))
            return rc;

        if ((rc = ReadPage(fd, pageNum, bufTable[slot].pData)) || (rc = hashTable.Insert(fd, pageNum, slot)) || (rc = InitPageDesc(fd, pageNum, slot))) {
            Unlink(slot);
            InsertFree(slot);
            return rc;
        }
    } else {
        if (!bMultiplePins && bufTable[slot].pinCount > 0)
            return PF_PAGEPINNED;

        bufTable[slot].pinCount++;

        if ((rc = Unlink(slot)) || (rc = LinkHead(slot)))
            return rc;
    }

    *ppBuffer = bufTable[slot].pData;

    return 0;
}

RC PF_BufferMgr::AllocatePage(int fd, PageNum pageNum, char **ppBuffer) {
    RC rc;
    int slot;

    if (!(rc = hashTable.Find(fd, pageNum, slot)))
        return PF_PAGEINBUF;
    else if (rc != PF_HASHNOTFOUND)
        return rc;

    if ((rc = InternalAlloc(slot)))
        return rc;

    if ((rc = hashTable.Insert(fd, pageNum, slot)) || (rc = InitPageDesc(fd, pageNum, slot))) {
        Unlink(slot);
        InsertFree(slot);
        return rc;
    }

    *ppBuffer = bufTable[slot].pData;

    return 0;
}

RC PF_BufferMgr::MarkDirty(int fd, PageNum pageNum) {
    RC rc;
    int slot;

    if ((rc = hashTable.Find(fd, pageNum, slot))) {
        if ((rc == PF_HASHNOTFOUND))
            return PF_PAGENOTINBUF;
        else
            return rc;
    }

    if (bufTable[slot].pinCount == 0)
        return PF_PAGEUNPINNED;
    
    bufTable[slot].bDirty = TRUE;

    if ((rc = Unlink(slot)) || (rc = LinkHead(slot)))
        return rc;
    
    return 0;
}

RC PF_BufferMgr::UnpinPage(int fd, PageNum pageNum) {
    RC rc;
    int slot;

    if ((rc = hashTable.Find(fd, pageNum, slot))) {
        if ((rc == PF_HASHNOTFOUND))
            return PF_PAGENOTINBUF;
        else
            return rc;
    }

    if (bufTable[slot].pinCount == 0)
        return PF_PAGEUNPINNED;
    
    if (--(bufTable[slot].pinCount) == 0) {
        if ((rc = Unlink(slot)) || (rc = LinkHead(slot)))
            return rc;
    }

    return 0;
}

RC PF_BufferMgr::FlushPages(int fd) {
    RC rc, rcWarn = 0;

    int slot = first;
    
    while (slot != INVALID_SLOT) {
        int next = bufTable[slot].next;

        if (bufTable[slot].fd == fd) {
            if (bufTable[slot].pinCount) {
                rcWarn = PF_PAGEPINNED;
            } else {
                if (bufTable[slot].bDirty) {
                    if ((rc = WritePage(fd, bufTable[slot].pageNum, bufTable[slot].pData)))
                        return rc;
                    bufTable[slot].bDirty = FALSE;
                }

                if ((rc = hashTable.Delete(fd, bufTable[slot].pageNum)) || (rc = Unlink(slot)) || (rc = InsertFree(slot)))
                    return rc;
            }
        }
        slot = next;
    }

    return rcWarn;
}

RC PF_BufferMgr::ForcePages(int fd, PageNum pageNum) {
    RC rc;

    int slot = first;
    while (slot != INVALID_SLOT) {
        int next = bufTable[slot].next;

        if (bufTable[slot].fd == fd && (pageNum==ALL_PAGES || bufTable[slot].pageNum == pageNum)) {
            if (bufTable[slot].bDirty) {
                if ((rc = WritePage(fd, bufTable[slot].pageNum, bufTable[slot].pData)))
                    return rc;
                bufTable[slot].bDirty = FALSE;
            }
        }

        slot = next;
    }

    return 0;
}

RC PF_BufferMgr::PrintBuffer() {
    std::cout << "Buffer contains " << numPages << " pages of size " << pageSize << ".\n";
    std::cout << "Contents in order from most recently used to " << "least recently used.\n";

   int slot, next;
   slot = first;
   while (slot != INVALID_SLOT) {
      next = bufTable[slot].next;
      std::cout << slot << " :: \n";
      std::cout << "  fd = " << bufTable[slot].fd << "\n";
      std::cout << "  pageNum = " << bufTable[slot].pageNum << "\n";
      std::cout << "  bDirty = " << bufTable[slot].bDirty << "\n";
      std::cout << "  pinCount = " << bufTable[slot].pinCount << "\n";
      slot = next;
   }

   if (first==INVALID_SLOT)
      std::cout << "Buffer is empty!\n";
   else
      std::cout << "All remaining slots are free.\n";

   return 0;
}

RC PF_BufferMgr::ClearBuffer() {
    RC rc;

    int slot, next;
    slot = first;
    while (slot != INVALID_SLOT) {
        next = bufTable[slot].next;
        if (bufTable[slot].pinCount == 0) {
            if ((rc = hashTable.Delete(bufTable[slot].fd, bufTable[slot].pageNum)) || (rc = Unlink(slot)) || (rc = InsertFree(slot)))
                return rc;
        }
        slot = next;
    }

    return 0;
}

RC PF_BufferMgr::ResizeBuffer(int iNewSize) {
    int i;
    RC rc;

    ClearBuffer();

    PF_BufPageDesc *pNewBufTable = new PF_BufPageDesc[iNewSize];

    for (i = 0; i < iNewSize; i++) {
        if ((pNewBufTable[i].pData = new char[pageSize]) == NULL) {
            std::cerr << "Not enough memory for buffer\n";
            exit(1);
        }

        memset((void *)pNewBufTable[i].pData, 0, pageSize);

        pNewBufTable[i].prev = i - 1;
        pNewBufTable[i].next = i + 1;
    }
    pNewBufTable[0].prev = pNewBufTable[iNewSize - 1].next = INVALID_SLOT;

    int oldFirst = first;
    PF_BufPageDesc *pOldBufTable = bufTable;

    numPages = iNewSize;
    first = last = INVALID_SLOT;
    free = 0;

    bufTable = pNewBufTable;

    int slot, next, newSlot;
    slot = oldFirst;
    while (slot != INVALID_SLOT) {
        next = pOldBufTable[slot].next;

        if ((rc = hashTable.Delete(pOldBufTable[slot].fd, pOldBufTable[slot].pageNum)))
            return rc;
        slot = next;
    }

    slot = oldFirst;
    while (slot != INVALID_SLOT) {
        next = pOldBufTable[slot].next;

        if ((rc = InternalAlloc(newSlot)))
            return rc;
        
        if ((rc = hashTable.Insert(pOldBufTable[slot].fd, pOldBufTable[slot].pageNum, newSlot)) || 
            (rc = InitPageDesc(pOldBufTable[slot].fd, pOldBufTable[slot].pageNum, newSlot)))
            return rc;
        
        Unlink(newSlot);
        InsertFree(newSlot);

        slot = next;
    }

    delete [] pOldBufTable;

    return 0;
}

RC PF_BufferMgr::InsertFree(int slot) {
    bufTable[slot].next  = free;
    free = slot;

    return 0;
}

RC PF_BufferMgr::LinkHead(int slot) {
    bufTable[slot].next = first;
    bufTable[slot].prev = INVALID_SLOT;

    if (first != INVALID_SLOT)
        bufTable[first].prev = slot;
    
    first = slot;

    if (last == INVALID_SLOT)
        last = first;
    
    return 0;
}

RC PF_BufferMgr::Unlink(int slot) {
    if (first == slot)
        first = bufTable[slot].next;
    
    if (last == slot)
        last = bufTable[slot].prev;
    
    if (bufTable[slot].next != INVALID_SLOT)
        bufTable[bufTable[slot].next].prev = bufTable[slot].prev;
    
    if (bufTable[slot].prev != INVALID_SLOT)
        bufTable[bufTable[slot].prev].next = bufTable[slot].next;
    
    bufTable[slot].prev = bufTable[slot].next = INVALID_SLOT;

    return 0;
}

RC PF_BufferMgr::InternalAlloc(int &slot) {
    RC rc;

    if (free != INVALID_SLOT) {
        slot = free;
        free = bufTable[slot].next;
    } else {
        for (slot = last; slot != INVALID_SLOT; slot = bufTable[slot].prev) {
            if (bufTable[slot].pinCount == 0)
                break;
        }

        if (slot == INVALID_SLOT)
            return PF_NOBUF;
        
        if (bufTable[slot].bDirty) {
            if ((rc = WritePage(bufTable[slot].fd, bufTable[slot].pageNum, bufTable[slot].pData)))
                return rc;
            
            bufTable[slot].bDirty = FALSE;
        }

        if ((rc = hashTable.Delete(bufTable[slot].fd, bufTable[slot].pageNum)) || (rc = Unlink(slot)))
            return rc;
    }

    if ((rc = LinkHead(slot)))
        return rc;
    
    return 0;
}

RC PF_BufferMgr::ReadPage(int fd, PageNum pageNum, char *dest) {
#ifdef PF_LOG
   char psMessage[100];
   sprintf (psMessage, "Reading (%d,%d).\n", fd, pageNum);
   WriteLog(psMessage);
#endif

    long offset = pageNum * (long)pageSize + PF_FILE_HDR_SIZE;
    if (lseek(fd, offset, L_SET) < 0)
        return PF_UNIX;
    
    int numBytes = read(fd, dest, pageSize);
    if (numBytes < 0)
        return PF_UNIX;
    else if (numBytes != pageSize)
        return PF_INCOMPLETEREAD;
    else
        return 0;
}

RC PF_BufferMgr::WritePage(int fd, PageNum pageNum, char *source) {
#ifdef PF_LOG
    char psMessage[100];
    sprintf(psMessage, "Writing (%d,%d).\n", fd, pageNum);
    WriteLog(psMessage);
#endif

    long offset = pageNum * (long)pageSize + PF_FILE_HDR_SIZE;
    if (lseek(fd, offset, L_SET) < 0)
        return PF_UNIX;
    
    int numBytes = write(fd, source, pageSize);
    if (numBytes < 0)
        return PF_UNIX;
    else if (numBytes != pageSize)
        return PF_INCOMPLETEWRITE;
    else
        return 0;
}

RC PF_BufferMgr::InitPageDesc(int fd, PageNum pageNum, int slot) {
    bufTable[slot].fd = fd;
    bufTable[slot].pageNum = pageNum;
    bufTable[slot].bDirty = FALSE;
    bufTable[slot].pinCount = 1;

    return 0;
}

#define MEMORY_FD -1

RC PF_BufferMgr::GetBlockSize(int &length) const {
    length = pageSize;
    return OK_RC;
}

RC PF_BufferMgr::AllocateBlock(char *&buffer) {
    RC rc = OK_RC;

    int slot;
    if ((rc = InternalAlloc(slot)) != OK_RC)
        return rc;
    
    PageNum pageNum = PageNum(reinterpret_cast<intptr_t>(bufTable[slot].pData));

    if ((rc = hashTable.Insert(MEMORY_FD, pageNum, slot) != OK_RC) || (rc = InitPageDesc(MEMORY_FD, pageNum, slot)) != OK_RC) {
        Unlink(slot);
        InsertFree(slot);
        return rc;
    }

    buffer = bufTable[slot].pData;

    return OK_RC;
}

RC PF_BufferMgr::DisposeBlock(char* buffer) {
    return UnpinPage(MEMORY_FD, PageNum(reinterpret_cast<intptr_t>(buffer)));
}