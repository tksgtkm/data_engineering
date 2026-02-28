#ifndef PROTODB_H
#define PROTODB_H

#include <iostream>
#include <cmath>
#include <cassert>

#define MAXNAME 24

typedef int RC;

#define START_PF_ERR  (-1)
#define END_PF_ERR    (-100)
#define START_RM_ERR  (-101)
#define END_RM_ERR    (-200)
#define START_IX_ERR  (-201)
#define END_IX_ERR    (-300)
#define START_SM_ERR  (-301)
#define END_SM_ERR    (-400)
#define START_QL_ERR  (-401)
#define END_QL_ERR    (-500)

#define START_PF_WARN  1
#define END_PF_WARN    100
#define START_RM_WARN  101
#define END_RM_WARN    200
#define START_IX_WARN  201
#define END_IX_WARN    300
#define START_SM_WARN  301
#define END_SM_WARN    400
#define START_QL_WARN  401
#define END_QL_WARN    500

#ifndef BOOLEAN
typedef char Boolean;
#endif

#ifndef FALSE
#define FALSE 0
#endif

#ifndef TRUE
#define TRUE 1
#endif

#ifndef NULL
#define NULL 0
#endif

#endif