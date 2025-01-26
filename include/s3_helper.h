#ifndef S3_HELPER_H
#define S3_HELPER_H

#include <aws/core/Aws.h>
#include <aws/s3/S3Client.h>
#include <aws/s3/model/PutObjectRequest.h>

#include <iostream>
#include <fstream>
#include <sys/stat.h>


#ifdef __cplusplus
extern "C" {
#endif
	

void myCppFunction();
//void UploadFileToS3(const Aws::String& bucketName, const Aws::String& objectName, const Aws::String& filePath);
void UploadFileToS3();
#ifdef __cplusplus
}
#endif


#endif
