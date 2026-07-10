#ifndef BookMDZipInflate_h
#define BookMDZipInflate_h

#include <stddef.h>

int BookMDInflateRawDeflate(
    const unsigned char *input,
    size_t inputSize,
    unsigned char *output,
    size_t outputSize
);

#endif
