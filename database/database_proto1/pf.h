/*
pf.h
paged file component
*/

#ifndef PF_H
#define PF_H

#include "protodb.h"

typedef int PageNum;

// 各ページにはヘッダー情報が格納される。
// PF_PageHdrはpf_internal.hで定義されており、格納する情報が含まれている。
// ここではsizeof(PF_PageHdr)を使えないが、int型なので使用する。
const int PF_PAGE_SIZE = 4096 - sizeof(int);


class PF_PageHandle {
    friend class PF_FileHandle;
public:
    PF_PageHandle();
    ~PF_PageHandle();

    PF_PageHandle(const PF_PageHandle &pageHandle);
    // オーバーロード
    PF_PageHandle& operator=(const PF_PageHandle &pageHandle);

    // pDataをページの内容を指すように設定する
    RC GetData(char *&pData) const;

    // ページナンバーを返す
    RC GetPageNum(PageNum &pageNum) const;

private:
    // ページナンバー
    int pageNum;
    // ページデータのポインター
    char *pPageData;
};

// ファイルのヘッダー構造
struct PF_FileHdr {
    // 連結リスト内の最初のフリーページ
    int firstFree;
    // ファイル内のページ番号
    int numPages;
};

// PFファイルインターフェース
class PF_BufferMgr;

class PF_FileHandle {
    friend class PF_Manager;
public:
    PF_FileHandle();
    ~PF_FileHandle();

    // コンストラクターのコピー
    PF_FileHandle (const PF_FileHandle &fileHandle);

    // オーバーロード
    PF_FileHandle& operator=(const PF_FileHandle &fileHandle);

    // 最初のページを取得する
    RC GetFirstPage(PF_PageHandle &pageHandle) const;
    // 現在のページの次のページを取得する
    RC GetThisPage(PageNum current, PF_PageHandle &pageHandle) const;
    // 特定のページを取得する
    RC GetThisPage(PageNum pageNum, PF_PageHandle &pageHandle) const;
    // 最後のページを取得する
    RC GetLastPage(PF_PageHandle &pageHandle) const;
    // 現在のページの前のページを取得する
    RC GetPrevPage(PageNum current, PF_PageHandle &pageHandle) const;

    // 新しいページの配分
    RC AllocatePage(PF_PageHandle &pageHandle);
    // ページの破棄
    RC DisposePage(PageNum pageNum);
    // ダーティページをマーキング
    RC MarkDirty(PageNum pageNum) const;
    // ページのマーキングを外す
    RC UnpinPage(PageNum pageNum) const;

    // バッファープールからページをフラッシュする
    // ダーティページはディスクに書き込まれる
    RC FlushPages() const;

    // ページを強制的にディスクに書き込む(バッファープールからは削除しない)
    RC ForcePages(PageNum pageNum=ALL_PAGES) const;

private:

    // ページナンバーが有効ならTRUE、それ以外はFALSE
    int IsValidPageNum(PageNum pageNum) const;

    // バッファーマネージャーのポインタ
    PF_BufferMgr *pBufferMgr;
    // ファイルヘッダー
    PF_FileHdr hdr;
    // ファイルオープンフラグ
    int bFileOpen;
    // ファイルヘッダーのダーティフラグ
    int bHdrChanged;
    // OSファイル記述子
    int unixfd;
};

void PF_PrintError(RC rc);

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