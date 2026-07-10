#include "BookMDZipInflate.h"
#include <zlib.h>

int BookMDInflateRawDeflate(
    const unsigned char *input,
    size_t inputSize,
    unsigned char *output,
    size_t outputSize
) {
    z_stream stream;
    stream.zalloc = Z_NULL;
    stream.zfree = Z_NULL;
    stream.opaque = Z_NULL;
    stream.avail_in = (uInt)inputSize;
    stream.next_in = (Bytef *)input;
    stream.avail_out = (uInt)outputSize;
    stream.next_out = output;

    int status = inflateInit2(&stream, -MAX_WBITS);
    if (status != Z_OK) {
        return status;
    }

    status = inflate(&stream, Z_FINISH);
    int endStatus = inflateEnd(&stream);
    if (status != Z_STREAM_END) {
        return status;
    }
    if (endStatus != Z_OK) {
        return endStatus;
    }
    return stream.total_out == outputSize ? Z_OK : Z_DATA_ERROR;
}
