#include <string.h>
#include <stdio.h>

#include "s3_wrapper.h"
#include "libs3.h"

#define FOPEN_EXTRA_FLAGS ""
#define SLEEP_UNITS_PER_SECOND 1

typedef struct growbuffer
{
    // The total number of bytes, and the start byte
    int size;
    // The start byte
    int start;
    // The blocks
    char data[64 * 1024];
    struct growbuffer *prev, *next;
} growbuffer;

static int showResponsePropertiesG = 0;
static S3Protocol protocolG = S3ProtocolHTTPS;
static S3UriStyle uriStyleG = S3UriStylePath;
static int retriesG = 5;
static int verifyPeerG = 0;
static const char *awsRegionG = "eu-north-1";
static int statusG = 0;
static char errorDetailsG[4096] = { 0 };

static const char* accessKeyIdG = 0;
static const char *secretAccessKeyG = 0;

typedef struct put_object_callback_data {
    FILE *infile;
    growbuffer *gb;
    uint64_t contentLength, originalContentLength;
    uint64_t totalContentLength, totalOriginalContentLength;
    int noStatus;
} put_object_callback_data;

static int should_retry()
{
    if (retriesG--) {
        // Sleep before next retry; start out with a 1 second sleep
        static int retrySleepInterval = 1 * SLEEP_UNITS_PER_SECOND;
        sleep(retrySleepInterval);
        // Next sleep 1 second longer
        retrySleepInterval++;
        return 1;
    }

    return 0;
}

static void growbuffer_read(growbuffer **gb, int amt, int *amtReturn,
                            char *buffer)
{
    *amtReturn = 0;

    growbuffer *buf = *gb;

    if (!buf) {
        return;
    }

    *amtReturn = (buf->size > amt) ? amt : buf->size;

    memcpy(buffer, &(buf->data[buf->start]), *amtReturn);

    buf->start += *amtReturn, buf->size -= *amtReturn;

    if (buf->size == 0) {
        if (buf->next == buf) {
            *gb = 0;
        }
        else {
            *gb = buf->next;
            buf->prev->next = buf->next;
            buf->next->prev = buf->prev;
        }
        free(buf);
        buf = NULL;
    }
}

static int putObjectDataCallback(int bufferSize, char *buffer,
                                 void *callbackData)
{
    put_object_callback_data *data =
        (put_object_callback_data *) callbackData;

    int ret = 0;

    if (data->contentLength) {
        int toRead = ((data->contentLength > (unsigned) bufferSize) ?
                      (unsigned) bufferSize : data->contentLength);
        if (data->gb) {
            growbuffer_read(&(data->gb), toRead, &ret, buffer);
        }
        else if (data->infile) {
            ret = fread(buffer, 1, toRead, data->infile);
        }
    }

    data->contentLength -= ret;
    data->totalContentLength -= ret;

    if (data->contentLength && !data->noStatus) {
        // Avoid a weird bug in MingW, which won't print the second integer
        // value properly when it's in the same call, so print separately
        printf("%llu bytes remaining ",
               (unsigned long long) data->totalContentLength);
        printf("(%d%% complete) ...\n",
               (int) (((data->totalOriginalContentLength -
                        data->totalContentLength) * 100) /
                      data->totalOriginalContentLength));
    }

    return ret;
}

// response properties callback ----------------------------------------------

// This callback does the same thing for every request type: prints out the
// properties if the user has requested them to be so
static S3Status responsePropertiesCallback
    (const S3ResponseProperties *properties, void *callbackData)
{
    (void) callbackData;

    if (!showResponsePropertiesG) {
        return S3StatusOK;
    }

#define print_nonnull(name, field)                                 \
    do {                                                           \
        if (properties-> field) {                                  \
            printf("%s: %s\n", name, properties-> field);          \
        }                                                          \
    } while (0)

    print_nonnull("Content-Type", contentType);
    print_nonnull("Request-Id", requestId);
    print_nonnull("Request-Id-2", requestId2);
    if (properties->contentLength > 0) {
        printf("Content-Length: %llu\n",
               (unsigned long long) properties->contentLength);
    }
    print_nonnull("Server", server);
    print_nonnull("ETag", eTag);
    if (properties->lastModified > 0) {
        char timebuf[256];
        time_t t = (time_t) properties->lastModified;
        // gmtime is not thread-safe but we don't care here.
        strftime(timebuf, sizeof(timebuf), "%Y-%m-%dT%H:%M:%SZ", gmtime(&t));
        printf("Last-Modified: %s\n", timebuf);
    }
    int i;
    for (i = 0; i < properties->metaDataCount; i++) {
        printf("x-amz-meta-%s: %s\n", properties->metaData[i].name,
               properties->metaData[i].value);
    }
    if (properties->usesServerSideEncryption) {
        printf("UsesServerSideEncryption: true\n");
    }

    return S3StatusOK;
}


// response complete callback ------------------------------------------------

// This callback does the same thing for every request type: saves the status
// and error stuff in global variables
static void responseCompleteCallback(S3Status status,
                                     const S3ErrorDetails *error,
                                     void *callbackData)
{
    (void) callbackData;

    statusG = status;
    // Compose the error details message now, although we might not use it.
    // Can't just save a pointer to [error] since it's not guaranteed to last
    // beyond this callback
    int len = 0;
    if (error && error->message) {
        len += snprintf(&(errorDetailsG[len]), sizeof(errorDetailsG) - len,
                        "  Message: %s\n", error->message);
    }
    if (error && error->resource) {
        len += snprintf(&(errorDetailsG[len]), sizeof(errorDetailsG) - len,
                        "  Resource: %s\n", error->resource);
    }
    if (error && error->furtherDetails) {
        len += snprintf(&(errorDetailsG[len]), sizeof(errorDetailsG) - len,
                        "  Further Details: %s\n", error->furtherDetails);
    }
    if (error && error->extraDetailsCount) {
        len += snprintf(&(errorDetailsG[len]), sizeof(errorDetailsG) - len,
                        "%s", "  Extra Details:\n");
        int i;
        for (i = 0; i < error->extraDetailsCount; i++) {
            len += snprintf(&(errorDetailsG[len]),
                            sizeof(errorDetailsG) - len, "    %s: %s\n",
                            error->extraDetails[i].name,
                            error->extraDetails[i].value);
        }
    }
}

void put_object() {

    // set bucket name and configuration info.
    accessKeyIdG = getenv("S3_ACCESS_KEY_ID");
    if (!accessKeyIdG) {
        fprintf(stderr, "Missing environment variable: S3_ACCESS_KEY_ID\n");
    }
    secretAccessKeyG = getenv("S3_SECRET_ACCESS_KEY");
    if (!secretAccessKeyG) {
        fprintf(stderr,"Missing environment variable: S3_SECRET_ACCESS_KEY\n");
    }

    // file transfer
    const char* filename = "test.txt";
    const char *bucketName = "s3-org";
    const char *key = "y";
    uint64_t contentLength = 0;
    int noStatus = 0;
    const char *cacheControl = 0, *contentType = 0, *md5 = 0;
    const char *contentDispositionFilename = 0, *contentEncoding = 0;
    int64_t expires = -1;
    S3NameValue metaProperties[S3_MAX_METADATA_COUNT];
    char useServerSideEncryption = 0;
    S3CannedAcl cannedAcl = S3CannedAclPrivate;
    int metaPropertiesCount = 0;

    // put_boject_callback function
    put_object_callback_data data;
    data.infile = 0;
    data.gb = 0;
    data.noStatus = noStatus;

    S3BucketContext bucketContext =
    {
        0,
        bucketName,
        protocolG,
        uriStyleG,
        accessKeyIdG,
        secretAccessKeyG,
        0,
        awsRegionG,
    };

    S3PutProperties putProperties =
    {
        contentType,
        md5,
        cacheControl,
        contentDispositionFilename,
        contentEncoding,
        expires,
        cannedAcl,
        metaPropertiesCount,
        metaProperties,
        useServerSideEncryption
    };

    if (!contentLength) {
        struct stat statbuf;
        if (stat(filename, &statbuf) == -1) {
            fprintf(stderr, "\nERROR: Failed to stat file %s: ", filename);
            perror(0);
            exit(-1);
        }
        contentLength = statbuf.st_size;

        // open file
        if (!(data.infile = fopen(filename, "r" FOPEN_EXTRA_FLAGS))) {
            fprintf(stderr, "\nERROR: Failed to open input file %s: ", filename);
            perror(0);
            exit(-1);
        }

        data.totalContentLength =
        data.totalOriginalContentLength =
        data.contentLength =
        data.originalContentLength =
            contentLength;

        // init S3
        S3Status status;
        const char *hostname = getenv("S3_HOSTNAME");
        if ((status = S3_initialize("s3", S3_INIT_ALL, hostname))
            != S3StatusOK) {
            fprintf(stderr, "Error! Failed to initialize s3\n");
        } else {
            fprintf(stderr, "S3 initialized success!\n");
        }

        S3PutObjectHandler putObjectHandler =
        {
            {&responsePropertiesCallback, &responseCompleteCallback},
            &putObjectDataCallback
        };

        do {
            S3_put_object(&bucketContext, key, contentLength, &putProperties, 0,
                    0, &putObjectHandler, &data);
        } while(S3_status_is_retryable(statusG) && should_retry());
    }
}

void test() {
	fprintf(stderr,"test!!!!\n");
}


