#pragma once


#include <aws/core/Aws.h>
#include <aws/s3/S3Client.h>
#include <aws/s3/model/BucketLocationConstraint.h>
#include <iostream>
#include <cstdint>
#include <cstdlib>


#ifdef __cplusplus
extern "C" {
#endif

namespace AwsDoc {
    namespace S3 {
        bool getObject(const Aws::String &objectKey,
                       const Aws::String &fromBucket,
                       const Aws::S3::S3ClientConfiguration &clientConfig);

        bool putObject(const Aws::String &bucketName,
                       const Aws::String &fileName,
                       const Aws::S3::S3ClientConfiguration &clientConfig);

        bool putObjectAcl(const Aws::String &bucketName, const Aws::String &objectKey, const Aws::String &ownerID,
                          const Aws::String &granteePermission, const Aws::String &granteeType,
                          const Aws::String &granteeID, const Aws::String &granteeEmailAddress,
                          const Aws::String &granteeURI, const Aws::S3::S3ClientConfiguration &clientConfig);

        bool putObjectAsync(const Aws::S3::S3Client &s3Client,
                            const Aws::String &bucketName,
                            const Aws::String &fileName);

    } // namespace S3
} // namespace AwsDoc

#ifdef __cplusplus
}
#endif

