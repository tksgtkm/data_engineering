#ifndef PF_BUFFERMGR_H
#define PF_BUFFERMGR_H

#include "pf_internal.h"
#include "pf_hashtable.h"

// INVALID_SLOTは、PF_BufPageDescのリストを追跡するPF_BufferMgrクラス内で使用されます。
// PF_BufPageDescの中には、次の項目と前の項目への整数型のポインタが含まれています。
// INVALID_SLOTは、前の項目も次の項目もないことを示すために使用されます。
#define INVALID_SLOT (-1)

// バッファ内のページに関するデータを含む構造体
struct PF_BufPageDesc {
    char *pData; // パージコンテンツ
    int next; // バッファーページ内の連結リストの次の項目
    int prev; // バッファーページ内の連結リストの前の項目
    int bDirty; // ページがダーティならTRUE
    short int pinCount; // ピンカウント
    PageNum pageNum; // 現ページの番号
    int fd; // 現ページのOSファイル記述子
};

// ページバッファーの管理
class PF_BufferMgr {
public:

    PF_BufferMgr (int numPages);

    ~PF_BufferMgr ();

    // バッファー内のページ番号を読み込み、その場所の*ppBufferを指すようにする
    RC GetPage (int fd, PageNum pageNum, char **ppBuffer, int bMultiplePins=TRUE);

    // バッファー内に新しいページを割り当て、その場所の*ppBufferを指すようにする
    RC AllocatePage(int fd, PageNum pageNum, char **ppBuffer);

    // ダーティページをマーキングする
    RC MarkDirty(int fd, PageNum pageNum);
    // バッファーからページを固定解除する
    RC UnpinPage(int fd, PageNum pageNum);
    // ファイルのページをフラッシュする
    RC FlushPages(int fd);

    // ページを強制的にディスクに書き込む(バッファープールからは削除しない)
    RC ForcePages(int fd, PageNum pageNum);

    RC ClearBuffer();

    RC PrintBuffer();

    RC ResizeBuffer(int iNewSize);

    RC GetBlockSize(int &length) const;

    RC AllocateBlock(char *&buffer);

    RC DisposeBLock(char *buffer);

private:
    RC InsertFree(int slot);
    RC LinkHead(int slot);
    RC Unlink(int slot);
    RC InternalAlloc(int &slot);

    RC ReadPage(int fd, PageNum pageNum, char *dest);

    RC WritePage(int fd, PageNum pageNum, char *source);

    RC InitPageDesc(int fd, PageNum pageNum, int slot);

    PF_BufPageDesc *bufTable;
    PF_HashTable hashTable;
    int numPages;
    int pageSize;
    int first;
    int last;
    int free;
};

#endif