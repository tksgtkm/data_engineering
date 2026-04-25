#ifndef PF_INTERNAL_H
#define PF_INTERNAL_H

#include <cstdlib>
#include <cstring>
#include "pf.h"

// バッファー内のページの数
const int PF_BUFFER_SIZE = 40;
// ハッシュテーブルのサイズ
const int PF_HASH_TBL_SIZE = 20;

// 所有者のみに読み書き権限が付与される
#define CREATION_MASK    0600
// フリーページのリストの終わり
#define PF_PAGE_LIST_END -1
// ページが使用されている
#define PF_PAGE_USED     -2

// L_SETはlseek関数のwhence引数を指定するために使用される
// /usr/include/unistd.hで定義されている
// 値が0の場合は指定された位置に移動する
#ifndef L_SET
#define L_SET
#endif

struct PF_PageHdr {
    // nextFreeには以下のいずれかの値を指定できます。
    // - 次の空きページ番号
    // - これが最後の空きページの場合はPF_PAGE_LIST_END
    // - ページが空きでない場合はPF_PAGE_USED
    int nextFree;
};

// ファイルヘッダーを1ページ分の長さに揃える
const int PF_FILE_HDR_SIZE = PF_PAGE_SIZE + sizeof(PF_PageHdr);

#endif