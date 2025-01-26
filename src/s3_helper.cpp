#include <iostream>
#include <fstream>
#include <aws/core/Aws.h>
#include <aws/s3/S3Client.h>
#include <aws/s3/model/PutObjectRequest.h>

#ifdef __cplusplus

//#include "s3_example.h"
extern "C" {
#endif
    void myCppFunction() {
        std::cout << "Hello from C++ function!" << std::endl;
    }

void UploadFileToS3() {
    Aws::SDKOptions options;
    Aws::InitAPI(options);
    {
        const Aws::String fileName = "test.txt";
        const Aws::String bucketName = "s3-org";

        Aws::S3::S3ClientConfiguration clientConfig;
        Aws::S3::S3Client s3Client(clientConfig);
        Aws::S3::Model::PutObjectRequest request;
        request.SetBucket(bucketName);
        request.SetKey(fileName);

        std::shared_ptr<Aws::IOStream> inputData =
            Aws::MakeShared<Aws::FStream>("SampleAllocationTag",
                                           fileName.c_str(),
                                           std::ios_base::in | std::ios_base::binary);

        if (!*inputData) {
            std::cerr << "Error unable to read file " << fileName << std::endl;
            return;
        }

        request.SetBody(inputData);
        Aws::S3::Model::PutObjectOutcome outcome = s3Client.PutObject(request);

        if (!outcome.IsSuccess()) {
            std::cerr << "Error: putObject: " << outcome.GetError().GetMessage() << std::endl;
        } else {
            std::cout << "Added object '" << fileName << "' to bucket '" << bucketName << "'." << std::endl;
        }
    }
    Aws::ShutdownAPI(options);
}

#ifdef __cplusplus
}
#endif

