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
    
}