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