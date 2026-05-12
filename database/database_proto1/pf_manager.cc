#include <cstdio>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include "pf_internal.h"
#include "pf_buffermgr.h"

PF_Manager::PF_Manager() {
    pBufferMgr = new PF_BufferMgr(PF_BUFFER_SIZE);
}

PF_Manager::~PF_Manager() {
    delete pBufferMgr;
}

RC PF_Manager::CreateFile(const char *fileName) {
    int fd;
    int numBytes;

    if ((fd = open(fileName, O_CREAT | O_EXCL | O_WRONLY, CREATION_MASK)) < 0)
        return PF_UNIX;
    
    char hdrBuf[PF_FILE_HDR_SIZE];

    memset(hdrBuf, 0, PF_FILE_HDR_SIZE);

    PF_FileHdr *hdr = (PF_FileHdr *)hdrBuf;
    hdr->firstFree = PF_PAGE_LIST_END;
    hdr->numPages = 0;

    if ((numBytes = write(fd, hdrBuf, PF_FILE_HDR_SIZE)) != PF_FILE_HDR_SIZE) {
        close(fd);
        unlink(fileName);

        if (numBytes < 0)
            return PF_UNIX;
        else
            return PF_HDRWRITE;
    }

    if(close(fd) < 0)
        return PF_UNIX;

    return 0;
}

RC PF_Manager::DestroyFile(const char *fileName) {
    if (unlink(fileName) < 0)
        return PF_UNIX;
    
    return 0;
}

RC PF_Manager::OpenFile(const char *fileName, PF_FileHandle &fileHandle) {
    int rc;

    if (fileHandle.bFileOpen)
        return PF_FILEOPEN;
    
    if ((fileHandle.unixfd = open(fileName, O_RDWR)) < 0)
        return PF_UNIX;
    
    {
        int numBytes = read(fileHandle.unixfd, (char *)&fileHandle.hdr, sizeof(PF_FileHdr));
        if (numBytes != sizeof(PF_FileHdr)) {
            rc = (numBytes < 0) ? PF_UNIX : PF_HDRREAD;
            goto err;
        }
    }

    fileHandle.bHdrChanged = FALSE;
    fileHandle.pBufferMgr = pBufferMgr;
    fileHandle.bFileOpen = TRUE;

    return 0;

err:
    close(fileHandle.unixfd);
    fileHandle.bFileOpen = FALSE;
    return rc;
}

RC PF_Manager::CloseFile(PF_FileHandle &fileHandle) {
    RC rc;

    if (!fileHandle.bFileOpen)
        return PF_CLOSEDFILE;

    if ((rc = fileHandle.FlushPages()))
        return rc;
    
    if (close(fileHandle.unixfd) < 0)
        return PF_UNIX;
    fileHandle.bFileOpen = FALSE;

    fileHandle.pBufferMgr = NULL;

    return 0;
}

RC PF_Manager::ClearBuffer() {
    return pBufferMgr->ClearBuffer();
}

RC PF_Manager::ResizeBuffer(int iNewSize) {
    return pBufferMgr->ResizeBuffer(iNewSize);
}

RC PF_Manager::GetBlockSize(int &length) const {
   return pBufferMgr->GetBlockSize(length);
}

RC PF_Manager::AllocateBlock(char *&buffer) {
   return pBufferMgr->AllocateBlock(buffer);
}

RC PF_Manager::DisposeBlock(char *buffer) {
   return pBufferMgr->DisposeBlock(buffer);
}