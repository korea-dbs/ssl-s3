#ifndef S3_WRAPPER_H
#define S3_WRAPPER_H

void upload_to_s3(const char* bucket_name, const char* key, const char* file_path);
void s3_wrapper_example(const char* msg);


#endif // S3_WRAPPER_H
