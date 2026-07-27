/*
 *
 * 覆盖场景：
 *   1.  正常 struct / union / enum 定义及 typedef
 *   2.  struct / union / enum 互相嵌套
 *   3.  struct / union / enum 关键字出现在结构体内部（成员声明）
 *   4.  struct / union / enum 作为函数返回值
 *   5.  struct / union / enum 作为函数参数
 *   6.  其他边界场景
 *   7.  三种类型两两嵌套（补充第 2 节未覆盖的组合）
 *   8.  三层及以上深度嵌套
 *   9.  同级多个嵌套类型
 *   10. 匿名与命名混合嵌套
 *   11. typedef 携带多层嵌套类型
 *   12. 嵌套类型中含函数指针 / 位域 / 数组
 *   13. 自引用指针嵌套
 *   14. 嵌套类型引用外部已定义类型
 *   15. 嵌套边界场景
 */

#include <stddef.h>
#define MY_STRUCT struct my_struct
#define MAX_BUF 256

/* ================================================================
 * 1. 正常情况
 * ================================================================ */

/* 1.1 普通struct */
struct point {
    int x;
    int y;
};

/* 1.2 普通union */
union data {
    int i;
    float f;
    char str[4];
};

/* 1.3 普通enum */
enum color {
    RED,
    GREEN,
    BLUE
};

/* 1.4 typedef struct（匿名标签，带别名） */
typedef struct {
    int id;
    char name[32];
} person_t;

/* 1.5 typedef union */
typedef union {
    int ival;
    double dval;
} value_t;

/* 1.6 typedef enum */
typedef enum {
    STATE_IDLE,
    STATE_RUN,
    STATE_STOP
} state_t;

/* 1.7 匿名struct变量声明（无typedef，无标签） */
struct {
    int a;
    int b;
} anon_var;

/* 1.8 带标签的typedef struct（自引用） */
typedef struct node {
    int val;
    struct node *next;
} node_t;

/* 1.9 多个typedef别名（逗号分隔） */
typedef struct {
    int x;
    int y;
    int z;
} coord_t, *coord_ptr_t;

/* 1.10 空结构体 */
struct empty {
};

/* 1.11 单成员结构体 */
struct single {
    int only;
};

/* ================================================================
 * 2. struct / union / enum 互相嵌套
 * ================================================================ */

/* 2.1 struct 内嵌套匿名union */
struct container {
    int type;
    union {
        int int_val;
        float float_val;
    } data;
};

/* 2.2 struct 内嵌套带标签enum */
struct task {
    enum priority { LOW, MED, HIGH } pri;
    void *payload;
};

/* 2.3 union 内嵌套匿名struct */
union packet {
    struct {
        unsigned char type;
        unsigned char length;
    } header;
    unsigned char raw[2];
};

/* 2.4 union 内嵌套带标签enum */
union flag_union {
    enum mode { AUTO, MANUAL } mode_val;
    int raw_flag;
};

/* 2.5 struct 内嵌套匿名struct */
struct outer_struct {
    int outer_field;
    struct {
        int inner_x;
        int inner_y;
    } inner;
};

/* 2.6 深度嵌套：struct -> union -> struct */
struct deep_nested {
    int level;
    union {
        struct {
            int a;
            int b;
        } s;
        int raw;
    } u;
};

/* 2.7 union 内嵌套 union */
union nested_union {
    union {
        int x;
        char bytes[4];
    } u1;
    long long_val;
};

/* 2.8 enum 带显式值 */
enum typed_enum {
    VAL_A = 1,
    VAL_B = 2,
    VAL_C = 4
};

/* ================================================================
 * 3. struct / union / enum 关键字出现在结构定义内部（成员声明）
 * ================================================================ */

/* 3.1 成员中使用关键字声明已知类型（非定义） */
struct with_member_decl {
    struct point pt;           /* struct 成员声明 */
    union data data_member;    /* union 成员声明 */
    enum color color_member;   /* enum 成员声明 */
};

/* 3.2 函数指针成员，参数含 struct / union / enum */
struct callback_holder {
    void (*on_event)(struct point *p);
    void (*on_data)(union data *d);
    int (*get_pri)(enum color c);
    int ref_count;
};

/* 3.3 const 成员声明 */
struct config {
    const struct point origin;
    enum color theme;
    int padding;
};

/* 3.4 struct 成员中同时有定义和声明 */
struct mixed_members {
    struct {
        int x;
        int y;
    } coords;
    struct point absolute;      /* 声明，非定义 */
    enum status { OK = 0, FAIL = 1 } status_val;
    enum color base_color;     /* 声明，非定义 */
};

/* ================================================================
 * 4. struct / union / enum 作为函数返回值
 * ================================================================ */

/* 4.1 直接返回 struct / union / enum */
struct point create_point(int x, int y);
union data get_data(void);
enum color get_color(void);

/* 4.2 返回指针 */
struct point *find_point(int id);
union data *alloc_data(int size);
enum color *parse_color(const char *s);

/* 4.3 const 返回指针 */
const struct point *get_origin(void);
const union data *peek_data(int idx);

/* 4.4 函数定义（带函数体），返回值为 struct */
struct point make_origin(void) {
    struct point p;
    p.x = 0;
    p.y = 0;
    return p;
}

/* 4.5 函数定义，返回值为 union */
union data default_data(void) {
    union data d;
    d.i = 0;
    return d;
}

/* ================================================================
 * 5. struct / union / enum 作为函数参数
 * ================================================================ */

/* 5.1 单个值参数 */
void draw_point(struct point p);
void set_data(union data d);
void set_color(enum color c);

/* 5.2 指针参数 */
void move_point(struct point *p, int dx, int dy);
void fill_data(union data *d, int type);
void apply_color(enum color *c);

/* 5.3 const 参数 */
void process_point(const struct point *p);
void handle_data(const union data *d);
void print_color(const enum color c);

/* 5.4 多参数混合 */
int transform(struct point *p, union data *d, enum color c, int flags);

/* 5.5 struct 出现在非首参数位置 */
void update(int id, struct point new_pos, enum color new_color);

/* 5.6 函数声明（带分号结尾，无函数体） */
struct point clone_point(struct point src, enum color tag);

/* ================================================================
 * 6. 其他边界场景
 * ================================================================ */

/* 6.1 带位域的 struct */
struct bits {
    unsigned int a : 1;
    unsigned int b : 3;
    unsigned int c : 4;
};

/* 6.2 sizeof 中使用 struct 关键字（应被跳过） */
int point_size = sizeof(struct point);

/* 6.3 强制类型转换中使用 struct 关键字（应被跳过） */
void *alloc_point(void) {
    return (struct point *)0;
}

/* 6.4 字符串常量中包含 struct 关键字 */
const char *type_name = "struct point";

/* 6.5 struct 中包含数组和函数指针 */
struct complex_struct {
    int values[16];
    void (*handler)(struct point *p, int count);
    struct point points[4];
};

/* 6.6 连续定义（无空行分隔） */
struct a { int x; };
struct b { int y; };
union c { int z; };
enum d { P, Q };

/* ================================================================
 * 7. 两两嵌套：
 * ================================================================ */

/* 7.1 struct 内嵌套匿名 enum */
struct se_anon {
    enum { NORTH, SOUTH, EAST, WEST } dir;
    int distance;
};

/* 7.2 union 内嵌套匿名 enum */
union ue_anon {
    enum { MODE_OFF, MODE_ON, MODE_SLEEP } state;
    int raw;
};

/* 7.3 struct 内嵌套命名 union */
struct su_named {
    int type;
    union named_data {
        int i;
        double d;
    } data;
};

/* 7.4 union 内嵌套命名 struct */
union us_named {
    struct named_point {
        int x;
        int y;
    } pt;
    int raw[2];
};

/* ================================================================
 * 8. 三层深度嵌套
 * ================================================================ */

/* 8.1 struct -> union -> enum（全匿名） */
struct deep_sue {
    int code;
    union {
        enum { ERR_NONE, ERR_WARN, ERR_FATAL } err;
        int err_code;
    } status;
};

/* 8.2 struct -> enum（无法直接嵌套 enum 体，但 enum 可作为成员） */
/* 用 struct -> struct -> enum 替代 */
struct deep_sse {
    struct {
        enum { OPT_A, OPT_B, OPT_C } opt;
        int value;
    } config;
    int padding;
};

/* 8.3 union -> struct -> union（全匿名） */
union deep_usu {
    struct {
        union {
            int x;
            char b[4];
        } u;
        int flag;
    } s;
    long all;
};

/* 8.4 union -> struct -> enum（全匿名） */
union deep_use {
    struct {
        enum { STATE_A, STATE_B } st;
        int data;
    } entry;
    int compact;
};

/* 8.5 四层：struct -> struct -> union -> struct */
struct deep_4lvl {
    struct {
        int outer;
        struct {
            union {
                struct {
                    int deep_field;
                } leaf;
                int leaf_raw;
            } mid;
        } inner;
    } outer_wrap;
};

/* 8.6 四层：union -> union -> struct -> enum */
union deep_4u {
    union {
        struct {
            enum { P0, P1, P2 } prio;
            int seq;
        } item;
        int raw;
    } layer1;
    long flat;
};

/* ================================================================
 * 9. 同级多个嵌套类型
 * ================================================================ */

/* 9.1 struct 中同级两个匿名 union */
struct multi_union {
    int type;
    union {
        int a;
        float b;
    } field1;
    union {
        char c;
        short d;
    } field2;
};

/* 9.2 struct 中同级匿名 union + 匿名 enum + 匿名 struct */
struct mixed_same_level {
    union {
        int u_val;
        float u_flt;
    } u_member;
    enum { M_LOW, M_HIGH } m_flag;
    struct {
        int s_a;
        int s_b;
    } s_member;
};

/* 9.3 union 中同级匿名 struct + 匿名 enum */
union multi_in_union {
    struct {
        int x;
        int y;
    } coord;
    enum { U_IDLE, U_ACTIVE } state;
};

/* 9.4 struct 中同级三个匿名 struct */
struct triple_nested {
    struct { int a; } first;
    struct { int b; } second;
    struct { int c; } third;
};

/* ================================================================
 * 10. 匿名与命名混合嵌套
 * ================================================================ */

/* 10.1 外层命名 struct，内层匿名 union + 匿名 enum */
struct mixed_outer_named {
    int id;
    union {
        int anon_int;
        float anon_flt;
    } anon_u;
    enum { MIX_START, MIX_END } anon_e;
};

/* 10.2 外层匿名 struct（typedef），内层命名 union */
typedef struct {
    int x;
    union named_inner {
        int i;
        char c;
    } inner;
} anon_outer_t;

/* 10.3 typedef union 内嵌套匿名 struct + 命名 enum */
typedef union {
    struct { int a; int b; } anon_s;
    enum named_inner_enum { E1, E2, E3 } named_e;
} hybrid_union_t;

/* 10.4 命名 struct 嵌套匿名 struct 嵌套命名 union */
struct complex_mix {
    struct {
        int level;
        union inner_data {
            int val;
            char buf[4];
        } data;
    } layer;
    int extra;
};

/* ================================================================
 * 11. typedef 携带多层嵌套类型
 * ================================================================ */

/* 11.1 typedef struct 含两层匿名嵌套 */
typedef struct {
    int type;
    union {
        struct {
            int x;
            int y;
        } pt;
        int raw;
    } u;
} point3d_t;

/* 11.2 typedef union 含 struct -> enum 嵌套 */
typedef union {
    struct {
        enum { K_DOWN, K_UP } kind;
        int code;
    } event;
    int packed;
} event_t;

/* 11.3 typedef struct 含同级 union + struct + enum */
typedef struct {
    union {
        int ival;
        float fval;
    } data;
    struct {
        int year;
        int month;
    } date;
    enum { FMT_BIN, FMT_TXT } format;
} record_t;

/* 11.4 多别名 typedef（含嵌套） */
typedef struct {
    int w;
    int h;
    union {
        int area;
        char bytes[4];
    } calc;
} rect_t, *rect_ptr_t;

/* ================================================================
 * 12. 嵌套类型中含函数指针 / 位域 / 数组
 * ================================================================ */

/* 12.1 struct 内匿名 union，union 内含函数指针 */
struct fp_in_nested {
    int tag;
    union {
        void (*cb_int)(int);
        void (*cb_str)(const char *);
    } handler;
};

/* 12.2 struct 内匿名 struct，struct 内含位域 */
struct bf_in_nested {
    int id;
    struct {
        unsigned int a : 1;
        unsigned int b : 3;
        unsigned int c : 4;
    } flags;
};

/* 12.3 struct 内匿名 union，union 内含数组 */
struct arr_in_nested {
    int len;
    union {
        int ints[4];
        char bytes[16];
    } buf;
};

/* 12.4 嵌套 struct 中含函数指针和位域混合 */
struct complex_nested {
    struct {
        unsigned int flag : 1;
        unsigned int type : 7;
        void (*on_event)(int, void *);
    } hdr;
    int payload[8];
};

/* 12.5 嵌套 union 中含 struct（带函数指针）+ enum */
union mixed_fp_enum {
    struct {
        int (*compare)(const void *, const void *);
        int size;
    } sortable;
    enum { SORT_IDLE, SORT_RUNNING, SORT_DONE } sort_state;
};

/* ================================================================
 * 13. 自引用指针嵌套
 * ================================================================ */

/* 13.1 struct 内引用自身（链表节点） */
struct link_node {
    int val;
    struct link_node *next;
};

/* 13.2 union 内引用自身（间接自引用） */
union self_ref {
    struct {
        int type;
        union self_ref *child;
    } node;
    int leaf_val;
};

/* 13.3 两个 struct 互相引用 */
struct node_a {
    int a_val;
    struct node_b *b_ptr;
};

struct node_b {
    int b_val;
    struct node_a *a_ptr;
};

/* 13.4 struct 内嵌套匿名 struct 含自引用指针 */
struct tree {
    int key;
    struct {
        struct tree *left;
        struct tree *right;
    } children;
};

/* ================================================================
 * 14. 嵌套类型引用外部已定义类型
 * ================================================================ */

/* 14.1 前置定义：struct 引用外部 struct / union / enum */
struct ext_point {
    int x;
    int y;
};

union ext_data {
    int i;
    double d;
};

enum ext_level {
    LVL_DEBUG,
    LVL_INFO,
    LVL_ERROR
};

struct ref_all_external {
    struct ext_point pt;
    union ext_data data;
    enum ext_level level;
    int extra;
};

/* 14.2 嵌套匿名 struct 中引用外部类型 */
struct ref_in_anon {
    struct {
        struct ext_point origin;
        enum ext_level severity;
    } meta;
    int count;
};

/* 14.3 typedef struct 引用外部类型 + 自定义嵌套 */
typedef struct {
    struct ext_point position;
    union {
        int raw;
        struct ext_point offset;
    } delta;
    enum ext_level log_level;
} geometry_t;

/* 14.4 union 中引用外部 struct 并同时定义匿名 struct */
union ref_and_define {
    struct ext_point external;
    struct {
        int compact_x;
        int compact_y;
    } internal;
};

/* ================================================================
 * 15. 嵌套边界场景
 * ================================================================ */

/* 15.1 空的嵌套匿名 struct */
struct empty_nested {
    struct {
    } empty_inner;
    int val;
};

/* 15.2 空的嵌套匿名 union */
struct empty_union_nested {
    union {
    } empty_u;
    int val;
};

/* 15.3 单成员嵌套类型 */
struct single_nested {
    union {
        int only;
    } u;
};

/* 15.4 struct 内嵌套匿名 union，无成员名（匿名联合体） */
struct anon_union_member {
    int tag;
    union {
        int a;
        int b;
    };
};

/* 15.5 struct 内嵌套匿名 struct，无成员名（匿名结构体） */
struct anon_struct_member {
    int type;
    struct {
        int inner_a;
        int inner_b;
    };
};

/* 15.6 连续嵌套定义 */
struct chain_a {
    union {
        struct {
            enum { CHAIN_X, CHAIN_Y } tag;
            int data;
        } s;
        int raw;
    } u;
};

/* 15.7 极深嵌套：struct -> union -> struct -> union -> enum */
struct very_deep {
    union {
        struct {
            union {
                enum { DEEP_0, DEEP_1, DEEP_2 } level;
                int pad;
            } layer2;
            int val;
        } layer1;
        int flat;
    } top;
};

/* ================================================================
 * 16. struct\union\enum 互相多重嵌套
 * ================================================================ */

/* 16.1 网状多重嵌套：每个节点均有多个子节点和多个父节点
 * 拓扑关系（-> 表示包含/引用）：
 *   mesh_root_a -> mesh_core, mesh_hub, mesh_leaf, mesh_state, mesh_root_b*
 *   mesh_root_b -> mesh_core, mesh_leaf, mesh_state, mesh_root_a*
 *   mesh_core   -> mesh_leaf, mesh_hub, mesh_state
 *   mesh_hub    -> mesh_leaf, mesh_state, mesh_core*
 *   mesh_leaf   -> mesh_state, mesh_core*, mesh_hub*
 * 父节点统计：
 *   mesh_state: leaf/hub/core/root_a/root_b   mesh_leaf: hub/core/root_a/root_b
 *   mesh_hub:   leaf/core/root_a              mesh_core: leaf/hub/root_a/root_b
 *   mesh_root_a: root_b                       mesh_root_b: root_a
 */
enum mesh_state {
    MESH_IDLE,
    MESH_BUSY,
    MESH_DONE
};

struct mesh_leaf {
    enum mesh_state state;
    struct mesh_core *core_ptr;  /* 回指上层，使 mesh_core 多一个父节点 */
    union mesh_hub *hub_ptr;     /* 回指上层，使 mesh_hub 多一个父节点 */
};

union mesh_hub {
    struct mesh_leaf leaf;
    enum mesh_state state;
    struct mesh_core *core_ptr;
    int raw;
};

struct mesh_core {
    struct mesh_leaf leaf;
    union mesh_hub hub;
    enum mesh_state state;
};

struct mesh_root_a {
    struct mesh_core core;
    union mesh_hub hub;
    struct mesh_leaf leaf;
    enum mesh_state state;
    union mesh_root_b *peer_b;   /* 互指，使两个根节点也拥有父节点 */
};

union mesh_root_b {
    struct mesh_core core;
    struct mesh_leaf leaf;
    enum mesh_state state;
    struct mesh_root_a *peer_a;
};