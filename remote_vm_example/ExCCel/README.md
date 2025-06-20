# ExCCel

*Disclaimer*: The backend formula parser, which compiles formulas into vm byte code, is not supposed to be vulnerable. You may not want to lose a lot of time searching for vulns in it.

## Processor

A little bit of help for reversing:

```c
struct raw_type {
    unsigned char len;
    unsigned char pad1[7];
    char data[CELL_DATA_SZ];
    unsigned long pad2;
};

typedef struct store_data {
    union {
        struct imm_type {
            unsigned int blob_idx;
        } imm;
        struct range_type {
            unsigned char x_start, y_start, x_end, y_end;
        } range;
    } data;
} store_data_t;

typedef struct value {
    unsigned char type;
    union {
        struct raw_type raw;
        struct store_data ref;
    } data;
} value_t;

```