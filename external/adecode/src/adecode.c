#include "adecode/adecode.h"

#include <limits.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define ACM_BUFFER_SIZE 512

#define ACM_FILE_ID 0x32897
#define ACM_FILE_VERSION 1

typedef int (*ReadBandFunc)(AudioDecoder* ad, int subband, int n);

typedef struct _byte_reader {
    AudioDecoderReadFunc* read;
    void* data;
    uint8_t* buf;
    int buf_size;
    uint8_t* buf_ptr;
    int buf_cnt;
} byte_reader;

typedef struct _bit_reader {
    byte_reader bytes;
    uint32_t data;
    int bitcnt;
} bit_reader;

typedef struct _AudioDecoder {
    bit_reader bits;
    int levels;
    int subbands;
    int samples_per_subband;
    int total_samples;
    int* prev_samples;
    int* samples;
    int block_samples_per_subband;
    int block_total_samples;
    int channels;
    int rate;
    int file_cnt;
    int* samp_ptr;
    int samp_cnt;
} AudioDecoder;

static int bytes_init(byte_reader* bytes, AudioDecoderReadFunc* read, void* data);
static unsigned char ByteReaderFill(byte_reader* bytes);
static int bits_init(bit_reader* bits, AudioDecoderReadFunc* read, void* data);
static void init_pack_tables(void);
static int ReadBand_Fail(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt0(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt3_16(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt17(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt18(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt19(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt20(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt21(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt22(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt23(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt24(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt26(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt27(AudioDecoder* ad, int subband, int n);
static int ReadBand_Fmt29(AudioDecoder* ad, int subband, int n);
static int ReadBands(AudioDecoder* ad);
static void untransform_subband0(int16_t* prv, int* buf, int step, int count);
static void untransform_subband(int* prv, int* buf, int step, int count);
static void untransform_all(AudioDecoder* ad);

static inline void requireBits(AudioDecoder* ad, int n)
{
    uint8_t b;

    while (ad->bits.bitcnt < n) {
        ad->bits.bytes.buf_cnt--;

        if (ad->bits.bytes.buf_cnt < 0) {
            b = ByteReaderFill(&(ad->bits.bytes));
        } else {
            b = *ad->bits.bytes.buf_ptr++;
        }
        ad->bits.data |= b << ad->bits.bitcnt;
        ad->bits.bitcnt += 8;
    }
}

#define takeBits(ad, n) ((ad)->bits.data & ((1 << (n)) - 1))

static inline void dropBits(AudioDecoder* ad, int n)
{
    ad->bits.data >>= n;
    ad->bits.bitcnt -= n;
}

static int AudioDecoder_cnt = 0;

static ReadBandFunc ReadBand_tbl[32] = {
    ReadBand_Fmt0,
    ReadBand_Fail,
    ReadBand_Fail,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt3_16,
    ReadBand_Fmt17,
    ReadBand_Fmt18,
    ReadBand_Fmt19,
    ReadBand_Fmt20,
    ReadBand_Fmt21,
    ReadBand_Fmt22,
    ReadBand_Fmt23,
    ReadBand_Fmt24,
    ReadBand_Fail,
    ReadBand_Fmt26,
    ReadBand_Fmt27,
    ReadBand_Fail,
    ReadBand_Fmt29,
    ReadBand_Fail,
    ReadBand_Fail,
};

static uint8_t pack11_2[128];

static uint8_t pack3_3[32];

static int16_t pack5_3[128];

static int16_t* AudioDecoder_scale0;

static int16_t* AudioDecoder_scale_tbl;

static int bytes_init(byte_reader* bytes, AudioDecoderReadFunc* read, void* data)
{
    bytes->read = read;
    bytes->data = data;

    bytes->buf = (uint8_t*)malloc(ACM_BUFFER_SIZE);
    if (bytes->buf == NULL) {
        return 0;
    }

    bytes->buf_size = ACM_BUFFER_SIZE;
    bytes->buf_cnt = 0;

    return 1;
}

static uint8_t ByteReaderFill(byte_reader* bytes)
{
    bytes->buf_cnt = bytes->read(bytes->data, bytes->buf, bytes->buf_size);
    if (bytes->buf_cnt == 0) {
        memset(bytes->buf, 0, bytes->buf_size);
        bytes->buf_cnt = bytes->buf_size;
    }

    bytes->buf_ptr = bytes->buf;
    bytes->buf_cnt -= 1;
    return *bytes->buf_ptr++;
}

static int bits_init(bit_reader* bits, AudioDecoderReadFunc* read, void* data)
{
    if (!bytes_init(&(bits->bytes), read, data)) {
        return 0;
    }

    bits->data = 0;
    bits->bitcnt = 0;

    return 1;
}

static void init_pack_tables(void)
{
    static int inited = 0;

    int i;
    int j;
    int m;

    if (inited) {
        return;
    }

    for (i = 0; i < 3; i++) {
        for (j = 0; j < 3; j++) {
            for (m = 0; m < 3; m++) {
                pack3_3[i + j * 3 + m * 9] = i + j * 4 + m * 16;
            }
        }
    }

    for (i = 0; i < 5; i++) {
        for (j = 0; j < 5; j++) {
            for (m = 0; m < 5; m++) {
                pack5_3[i + j * 5 + m * 25] = i + j * 8 + m * 64;
            }
        }
    }

    for (i = 0; i < 11; i++) {
        for (j = 0; j < 11; j++) {
            pack11_2[i + j * 11] = i + j * 16;
        }
    }

    inited = 1;
}

static int ReadBand_Fail(AudioDecoder* ad, int subband, int n)
{
    (void)ad;
    (void)subband;
    (void)n;

    return 0;
}

static int ReadBand_Fmt0(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int i;

    (void)n;

    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        *dst = 0;
        dst += ad->subbands;

        --i;
    }

    return 1;
}

static int ReadBand_Fmt3_16(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int16_t* scale;
    int value;
    int i;

    scale = &(AudioDecoder_scale0[-(1 << (n - 1))]);
    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        requireBits(ad, n);
        value = takeBits(ad, n);
        dropBits(ad, n);

        *dst = scale[value];
        dst += ad->subbands;

        --i;
    }

    return 1;
}

static int ReadBand_Fmt17(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int16_t* scale;
    int value;
    int i;

    (void)n;

    scale = AudioDecoder_scale0;
    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        requireBits(ad, 3);
        value = takeBits(ad, 3);

        if ((value & 0x01) == 0) {
            dropBits(ad, 1);

            *dst = 0;
            dst += ad->subbands;

            if (--i == 0) {
                break;
            }

            *dst = 0;
            dst += ad->subbands;
        } else if ((value & 0x02) == 0) {
            dropBits(ad, 2);

            *dst = 0;
            dst += ad->subbands;
        } else {
            dropBits(ad, 3);

            if ((value & 0x04) != 0) {
                *dst = scale[1];
            } else {
                *dst = scale[-1];
            }

            dst += ad->subbands;
        }

        --i;
    }

    return 1;
}

static int ReadBand_Fmt18(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int16_t* scale;
    int value;
    int i;

    (void)n;

    scale = AudioDecoder_scale0;
    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        requireBits(ad, 2);
        value = takeBits(ad, 2);

        if ((value & 0x01) == 0) {
            dropBits(ad, 1);

            *dst = 0;
            dst += ad->subbands;
        } else {
            dropBits(ad, 2);

            if ((value & 0x02) != 0) {
                *dst = scale[1];
            } else {
                *dst = scale[-1];
            }

            dst += ad->subbands;
        }

        --i;
    }

    return 1;
}

static int ReadBand_Fmt19(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int16_t* scale;
    int value;
    int i;
    uint8_t code;

    (void)n;

    scale = &(AudioDecoder_scale0[-1]);
    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        requireBits(ad, 5);
        value = takeBits(ad, 5);
        dropBits(ad, 5);

        code = pack3_3[value];

        *dst = scale[code & 0x03];
        dst += ad->subbands;
        if (--i == 0) {
            break;
        }

        *dst = scale[(code >> 2) & 0x03];
        dst += ad->subbands;
        if (--i == 0) {
            break;
        }

        *dst = scale[code >> 4];
        dst += ad->subbands;
        --i;
    }

    return 1;
}

static int ReadBand_Fmt20(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int16_t* scale;
    int value;
    int i;

    (void)n;

    scale = AudioDecoder_scale0;
    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        requireBits(ad, 4);
        value = takeBits(ad, 4);

        if ((value & 0x01) == 0) {
            dropBits(ad, 1);

            *dst = 0;
            dst += ad->subbands;
            --i;

            if (i == 0) {
                break;
            }

            *dst = 0;
            dst += ad->subbands;
            --i;
        } else if ((value & 0x02) == 0) {
            dropBits(ad, 2);

            *dst = 0;
            dst += ad->subbands;
            --i;
        } else {
            dropBits(ad, 4);

            if ((value & 0x08) != 0) {
                if ((value & 0x04) != 0) {
                    *dst = scale[2];
                } else {
                    *dst = scale[1];
                }
            } else {
                if (value & 0x04) {
                    *dst = scale[-1];
                } else {
                    *dst = scale[-2];
                }
            }

            dst += ad->subbands;
            --i;
        }
    }

    return 1;
}

static int ReadBand_Fmt21(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int16_t* scale;
    int value;
    int i;

    (void)n;

    scale = AudioDecoder_scale0;
    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        requireBits(ad, 3);
        value = takeBits(ad, 3);

        if ((value & 0x01) == 0) {
            dropBits(ad, 1);

            *dst = 0;
            dst += ad->subbands;
            --i;
        } else {
            dropBits(ad, 3);

            if ((value & 0x04) != 0) {
                if ((value & 0x02) != 0) {
                    *dst = scale[2];
                } else {
                    *dst = scale[1];
                }
            } else {
                if (value & 0x02) {
                    *dst = scale[-1];
                } else {
                    *dst = scale[-2];
                }
            }

            dst += ad->subbands;
            --i;
        }
    }

    return 1;
}

static int ReadBand_Fmt22(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int16_t* scale;
    int value;
    int i;
    uint16_t code;

    (void)n;

    scale = &(AudioDecoder_scale0[-2]);
    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        requireBits(ad, 7);
        value = takeBits(ad, 7);
        dropBits(ad, 7);

        code = pack5_3[value];

        *dst = scale[code & 7];
        dst += ad->subbands;
        --i;

        if (i == 0) {
            break;
        }

        *dst = scale[((code >> 3) & 7)];
        dst += ad->subbands;
        --i;

        if (i == 0) {
            break;
        }

        *dst = scale[code >> 6];
        dst += ad->subbands;
        --i;
    }

    return 1;
}

static int ReadBand_Fmt23(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int16_t* scale;
    int value;
    int i;

    (void)n;

    scale = AudioDecoder_scale0;
    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        requireBits(ad, 5);
        value = takeBits(ad, 5);

        if ((value & 0x01) == 0) {
            dropBits(ad, 1);

            *dst = 0;
            dst += ad->subbands;
            --i;

            if (i == 0) {
                break;
            }

            *dst = 0;
            dst += ad->subbands;
            --i;
        } else if ((value & 0x02) == 0) {
            dropBits(ad, 2);

            *dst = 0;
            dst += ad->subbands;
            --i;
        } else if ((value & 0x04) == 0) {
            dropBits(ad, 4);

            if (value & 0x08) {
                *dst = scale[1];
            } else {
                *dst = scale[-1];
            }

            dst += ad->subbands;
            --i;
        } else {
            dropBits(ad, 5);

            value >>= 3;
            value &= 0x03;
            if (value > 1) {
                value += 3;
            }

            *dst = scale[value - 3];
            dst += ad->subbands;
            --i;
        }
    }

    return 1;
}

static int ReadBand_Fmt24(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int16_t* scale;
    int value;
    int i;

    (void)n;

    scale = AudioDecoder_scale0;
    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        requireBits(ad, 4);
        value = takeBits(ad, 4);

        if ((value & 0x01) == 0) {
            dropBits(ad, 1);

            *dst = 0;
            dst += ad->subbands;
            --i;
        } else if ((value & 0x02) == 0) {
            dropBits(ad, 3);

            if ((value & 0x04) != 0) {
                *dst = scale[1];
            } else {
                *dst = scale[-1];
            }

            dst += ad->subbands;
            --i;
        } else {
            dropBits(ad, 4);

            value >>= 2;
            value &= 0x03;
            if (value > 1) {
                value += 3;
            }

            *dst = scale[value - 3];
            dst += ad->subbands;
            --i;
        }
    }

    return 1;
}

static int ReadBand_Fmt26(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int16_t* scale;
    int value;
    int i;

    (void)n;

    scale = AudioDecoder_scale0;
    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        requireBits(ad, 5);
        value = takeBits(ad, 5);

        if ((value & 0x01) == 0) {
            dropBits(ad, 1);

            *dst = 0;
            dst += ad->subbands;
            --i;

            if (i == 0) {
                break;
            }

            *dst = 0;
            dst += ad->subbands;
            --i;
        } else if ((value & 0x02) == 0) {
            dropBits(ad, 2);

            *dst = 0;
            dst += ad->subbands;
            --i;

        } else {
            dropBits(ad, 5);

            value >>= 2;
            value &= 0x07;
            if (value > 3) {
                value += 1;
            }

            *dst = scale[value - 4];
            dst += ad->subbands;
            --i;
        }
    }

    return 1;
}

static int ReadBand_Fmt27(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int16_t* scale;
    int value;
    int i;

    (void)n;

    scale = AudioDecoder_scale0;
    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        requireBits(ad, 4);
        value = takeBits(ad, 4);

        if ((value & 0x01) == 0) {
            dropBits(ad, 1);

            *dst = 0;
            dst += ad->subbands;
            --i;
        } else {
            dropBits(ad, 4);

            value >>= 1;
            value &= 0x07;
            if (value > 3) {
                value += 1;
            }

            *dst = scale[value - 4];
            dst += ad->subbands;
            --i;
        }
    }

    return 1;
}

static int ReadBand_Fmt29(AudioDecoder* ad, int subband, int n)
{
    int* dst;
    int16_t* scale;
    int value;
    int i;
    uint8_t code;

    (void)n;

    scale = AudioDecoder_scale0;
    dst = &(ad->samples[subband]);

    i = ad->samples_per_subband;
    while (i != 0) {
        requireBits(ad, 7);
        value = takeBits(ad, 7);
        dropBits(ad, 7);

        code = pack11_2[value];

        *dst = scale[(code & 0x0F) - 5];
        dst += ad->subbands;
        --i;

        if (i == 0) {
            break;
        }

        *dst = scale[(code >> 4) - 5];
        dst += ad->subbands;
        --i;
    }

    return 1;
}

static int ReadBands(AudioDecoder* ad)
{
    int bits;
    int scale_step;
    int16_t* scale;
    int sum;
    int i;
    int n;

    requireBits(ad, 4);
    bits = 1 << takeBits(ad, 4);
    dropBits(ad, 4);

    requireBits(ad, 16);
    scale_step = (int16_t)takeBits(ad, 16);
    dropBits(ad, 16);

    scale = AudioDecoder_scale0;
    i = bits;
    sum = 0;
    while (i != 0) {
        *scale++ = sum;
        sum += scale_step;
        --i;
    }

    scale = &(AudioDecoder_scale0[-1]);
    i = bits;
    sum = -scale_step;
    while (i != 0) {
        *scale-- = sum;
        sum -= scale_step;
        --i;
    }

    init_pack_tables();

    for (i = 0; i < ad->subbands; i++) {
        requireBits(ad, 5);
        n = takeBits(ad, 5);
        dropBits(ad, 5);

        if (!ReadBand_tbl[n](ad, i, n)) {
            return 0;
        }
    }
    return 1;
}

static void untransform_subband0(int16_t* prv, int* buf, int step, int count)
{
    int i;
    int h1;
    int h2;
    int l1;
    int l2;

    if (count == 2) {
        for (i = step; i != 0; i--) {
            l2 = prv[0];
            h2 = prv[1];

            l1 = buf[0];
            buf[0] = 2 * h2 + l2 + l1;

            h1 = buf[step];
            buf[step] = 2 * l1 - h2 - h1;

            prv[0] = (int16_t)l1;
            prv[1] = (int16_t)h1;

            prv += 2;
            buf += 1;
        }
    } else if (count == 4) {
        for (i = step; i != 0; i--) {
            l1 = prv[0];
            h1 = prv[1];

            l2 = buf[0];
            buf[0] = 2 * h1 + l1 + l2;

            h2 = buf[step];
            buf[step] = 2 * l2 - h1 - h2;

            l1 = buf[step * 2];
            buf[step * 2] = 2 * h2 + l2 + l1;

            h1 = buf[step * 3];
            buf[step * 3] = 2 * l1 - h2 - h1;

            prv[0] = (int16_t)l1;
            prv[1] = (int16_t)h1;

            prv += 2;
            buf++;
        }
    } else {
        for (i = step; i != 0; i--) {
            int c = count >> 2;
            int* b = buf;

            if ((count & 2) != 0) {
                l2 = prv[0];
                h2 = prv[1];

                l1 = buf[0];
                buf[0] = 2 * h2 + l2 + l1;

                h1 = buf[step];
                buf[step] = 2 * l2 - h2 - h1;
            } else {
                l1 = prv[0];
                h1 = prv[1];
            }

            while (c != 0) {
                l2 = b[0];
                b[0] = 2 * h1 + l1 + l2;

                h2 = b[step];
                b[step] = 2 * l2 - h1 - h2;

                l1 = b[step * 2];
                b[step * 2] = 2 * h2 + l2 + l1;

                h1 = b[step * 3];
                b[step * 3] = 2 * l1 - h2 - h1;

                b += step * 4;
                c--;
            }

            prv[0] = (int16_t)l1;
            prv[1] = (int16_t)h1;

            prv += 2;
            buf += 1;
        }
    }
}

static void untransform_subband(int* prv, int* buf, int step, int count)
{
    int i;
    int h1;
    int h2;
    int l1;
    int l2;

    if (count == 4) {
        for (i = step; i != 0; i--) {
            l1 = prv[0];
            h1 = prv[1];

            l2 = buf[0];
            buf[0] = 2 * h1 + l1 + l2;

            h2 = buf[step];
            buf[step] = 2 * l2 - h1 - h2;

            l1 = buf[step * 2];
            buf[step * 2] = 2 * h2 + l2 + l1;

            h1 = buf[step * 3];
            buf[step * 3] = 2 * l1 - h2 - h1;

            prv[0] = l1;
            prv[1] = h1;

            prv += 2;
            buf += 1;
        }
    } else {
        for (i = step; i != 0; i--) {
            int c = count >> 2;
            int* b = buf;

            l1 = prv[0];
            h1 = prv[1];

            while (c != 0) {
                l2 = b[0];
                b[0] = 2 * h1 + l1 + l2;

                h2 = b[step];
                b[step] = 2 * l2 - h1 - h2;

                l1 = b[step * 2];
                b[step * 2] = 2 * h2 + l2 + l1;

                h1 = b[step * 3];
                b[step * 3] = 2 * l1 - h2 - h1;

                b += step * 4;
                c--;
            }

            prv[0] = l1;
            prv[1] = h1;

            prv += 2;
            buf += 1;
        }
    }
}

static void untransform_all(AudioDecoder* ad)
{
    int rem_samples_per_subband;
    int* buf_base;
    int step;
    int count;
    int* prv;
    int i;
    int* buf;

    if (ad->levels == 0) {
        return;
    }

    buf_base = ad->samples;

    rem_samples_per_subband = ad->samples_per_subband;
    while (rem_samples_per_subband > 0) {
        step = ad->subbands >> 1;
        count = ad->block_samples_per_subband;
        if (count > rem_samples_per_subband) {
            count = rem_samples_per_subband;
        }

        count *= 2;

        untransform_subband0((int16_t*)ad->prev_samples, buf_base, step, count);
        buf = buf_base;
        prv = &(ad->prev_samples[step]);

        for (i = 0; i < count; i++) {
            *buf += 1;
            buf += step;
        }

        step >>= 1;
        count *= 2;

        while (step != 0) {
            untransform_subband(prv, buf_base, step, count);
            prv += step * 2;
            count *= 2;
            step >>= 1;
        }

        buf_base += ad->block_total_samples;
        rem_samples_per_subband -= ad->block_samples_per_subband;
    }
}

static int AudioDecoder_fill(AudioDecoder* ad)
{
    if (!ReadBands(ad)) {
        return 0;
    }

    untransform_all(ad);

    ad->file_cnt -= ad->total_samples;
    ad->samp_ptr = ad->samples;
    ad->samp_cnt = ad->total_samples;

    if (ad->file_cnt < 0) {
        ad->samp_cnt += ad->file_cnt;
        ad->file_cnt = 0;
    }

    return 1;
}

unsigned int AudioDecoder_Read(AudioDecoder* ad, void* buffer, unsigned int qty)
{
    uint16_t* dst;
    int* samp_ptr;
    int samp_cnt;
    unsigned int i;

    dst = (uint16_t*)buffer;
    samp_ptr = ad->samp_ptr;
    samp_cnt = ad->samp_cnt;

    for (i = 0; i < qty; i += 2) {
        if (samp_cnt == 0) {
            if (ad->file_cnt == 0) {
                break;
            }

            if (!AudioDecoder_fill(ad)) {
                break;
            }

            samp_ptr = ad->samp_ptr;
            samp_cnt = ad->samp_cnt;
        }

        *dst++ = (uint16_t)((*samp_ptr++) >> ad->levels);
        samp_cnt--;
    }

    ad->samp_ptr = samp_ptr;
    ad->samp_cnt = samp_cnt;

    return i;
}

void AudioDecoder_Close(AudioDecoder* ad)
{
    if (ad->bits.bytes.buf != NULL) {
        free(ad->bits.bytes.buf);
    }

    if (ad->prev_samples != NULL) {
        free(ad->prev_samples);
    }

    if (ad->samples != NULL) {
        free(ad->samples);
    }

    free(ad);

    AudioDecoder_cnt--;

    if (AudioDecoder_cnt == 0) {
        if (AudioDecoder_scale_tbl != NULL) {
            free(AudioDecoder_scale_tbl);
            AudioDecoder_scale_tbl = NULL;
        }
    }
}

AudioDecoder* Create_AudioDecoder(AudioDecoderReadFunc* reader, void* data, int* channels, int* sampleRate, int* sampleCount)
{
    unsigned int tmp;
    int prev_samples_length;
    AudioDecoder* ad;

    ad = (AudioDecoder*)malloc(sizeof(AudioDecoder));
    if (ad == NULL) {
        return NULL;
    }

    memset(ad, 0, sizeof(AudioDecoder));

    AudioDecoder_cnt++;

    if (!bits_init(&(ad->bits), reader, data)) {
        goto error;
    }

    requireBits(ad, 24);
    tmp = takeBits(ad, 24);
    dropBits(ad, 24);

    if (tmp != ACM_FILE_ID) {
        goto error;
    }

    requireBits(ad, 8);
    tmp = takeBits(ad, 8);
    dropBits(ad, 8);

    if (tmp != ACM_FILE_VERSION) {
        goto error;
    }

    requireBits(ad, 16);
    ad->file_cnt = takeBits(ad, 16);
    dropBits(ad, 16);

    requireBits(ad, 16);
    ad->file_cnt |= takeBits(ad, 16) << 16;
    dropBits(ad, 16);

    requireBits(ad, 16);
    ad->channels = takeBits(ad, 16);
    dropBits(ad, 16);

    requireBits(ad, 16);
    ad->rate = takeBits(ad, 16);
    dropBits(ad, 16);

    requireBits(ad, 4);
    ad->levels = takeBits(ad, 4);
    dropBits(ad, 4);

    requireBits(ad, 12);
    ad->subbands = 1 << ad->levels;
    ad->samples_per_subband = takeBits(ad, 12);
    ad->total_samples = ad->samples_per_subband * ad->subbands;
    dropBits(ad, 12);

    if (ad->levels != 0) {
        prev_samples_length = 3 * ad->subbands / 2 - 2;
    } else {
        prev_samples_length = 0;
    }

    ad->block_samples_per_subband = 2048 / ad->subbands - 2;
    if (ad->block_samples_per_subband < 1) {
        ad->block_samples_per_subband = 1;
    }

    ad->block_total_samples = ad->block_samples_per_subband * ad->subbands;

    if (prev_samples_length != 0) {
        ad->prev_samples = (int*)malloc(sizeof(int) * prev_samples_length);
        if (ad->prev_samples == NULL) {
            goto error;
        }

        memset(ad->prev_samples, 0, sizeof(int) * prev_samples_length);
    }

    ad->samples = (int*)malloc(sizeof(int) * ad->total_samples);
    if (ad->samples == NULL) {
        goto error;
    }

    ad->samp_cnt = 0;

    if (AudioDecoder_cnt == 1) {
        AudioDecoder_scale_tbl = (int16_t*)malloc(sizeof(int16_t) * 0x8000 * 2);
        AudioDecoder_scale0 = &(AudioDecoder_scale_tbl[0x8000]);
    }

    *channels = ad->channels;
    *sampleRate = ad->rate;
    *sampleCount = ad->file_cnt;

    return ad;

error:

    AudioDecoder_Close(ad);

    *channels = 0;
    *sampleRate = 0;
    *sampleCount = 0;

    return NULL;
}
