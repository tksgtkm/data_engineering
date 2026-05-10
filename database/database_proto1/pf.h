/*
pf.h
paged file component
*/

#ifndef PF_H
#define PF_H

#include "protodb.h"

typedef int PageNum;

const int PF_PAGE_SIZE = 4096 - sizeof(int);

class PF_PageHandle {
    friend class PF_FileHandle;
public:
    PF_PageHandle();
    ~PF_PageHandle();

    PF_PageHandle(const PF_PageHandle &pageHandle);
    PF_PageHandle& operator=(const PF_PageHandle &pageHandle);

    RC GetData(char *&pData) const;

    RC GetPageNum(PageNum &pageNum) const;

private:
    int pageNum;
    char *pPageData;
};

// ファイルのヘッダー構造
struct PF_FileHdr {
    int firstFree;
    int numPages;
};

class PF_BufferMgr;

#define PF_PAGEPINNED      (START_PF_WARN + 0)
#define PF_PAGENOTINBUF    (START_PF_WARN + 1)
#define PF_INVALIDPAGE     (START_PF_WARN + 2)
#define PF_FILEOPEN        (START_PF_WARN + 3)
#define PF_CLOSEDFILE      (START_PF_WARN + 4)
#define PF_PAGEFREE        (START_PF_WARN + 5)
#define PF_PAGEUNPINNED    (START_PF_WARN + 6)
#define PF_EOF             (START_PF_WARN + 7)
#define PF_TOOSMALL        (START_PF_WARN + 8)
#define PF_LASTWARN        PF_TOOSMALL

#define PF_NOMEM           (START_PF_ERR - 0)
#define PF_NOBUF           (START_PF_ERR - 1)
#define PF_INCOMPLETEREAD  (START_PF_ERR - 2)
#define PF_INCOMPLETEWRITE (START_PF_ERR - 3)
#define PF_HDRREAD         (START_PF_ERR - 4)
#define PF_HDRWRITE        (START_PF_ERR - 5)

#define PF_PAGEINBUF       (START_PF_ERR - 6)
#define PF_HASHNOTFOUND    (START_PF_ERR - 7)
#define PF_HASHPAGEEXIST   (START_PF_ERR - 8)
#define PF_INVALIDNAME     (START_PF_ERR - 9)

#define PF_UNIX            (START_PF_ERR - 10)
#define PF_LASTERROR       PF_UNIX

#endif