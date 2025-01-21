#include <aws/core/Aws.h>
#include <aws/s3/S3Client.h>
#include <aws/s3/model/PutObjectRequest.h>
#include <fstream>
#include <iostream>

#include <string>
#include <cstdlib>

inline void loadEnv(const std::string& filename) {
    std::ifstream file(filename);
    std::string line;

    while (std::getline(file, line)) {
        size_t pos = line.find('=');
        if (pos != std::string::npos) {
            std::string key = line.substr(0, pos);
            std::string value = line.substr(pos + 1);
            setenv(key.c_str(), value.c_str(), 1); // 환경 변수 설정
        }
    }
}

void s3_wrapper_example(const char* msg) {
	std::cout << "Msg: " << msg << std::endl;
	loadEnv("../src/.env");
	const char* bucketName = std::getenv("AWS_S3_BUCKET_NAME");	
	const char* s3Key = std::getenv("AWS_S3_KEY");
	std::cout << "Bucket Name: " << bucketName << std::endl;
	std::cout << "S3 Key: " << s3Key << std::endl;

	Aws::SDKOptions options;
	Aws::InitAPI(options);
	{
		std::cout << "init API!!!\n";
	}
	Aws::ShutdownAPI(options);
}

void upload_to_s3(const char* bucket_name, const char* key, const char* file_path) {
    Aws::SDKOptions options;
    Aws::InitAPI(options);
    {
        Aws::S3::S3Client s3_client;
        Aws::S3::Model::PutObjectRequest object_request;
        object_request.SetBucket(bucket_name);
        object_request.SetKey(key);

        auto data_stream = Aws::MakeShared<Aws::FStream>("S3UploaderTag",
                                                         file_path,
                                                         std::ios_base::in | std::ios_base::binary);
        object_request.SetBody(data_stream);

        auto outcome = s3_client.PutObject(object_request);
        if (outcome.IsSuccess()) {
            std::cout << "S3 upload succeeded!" << std::endl;
        } else {
            std::cerr << "S3 upload failed: " 
                      << outcome.GetError().GetMessage() << std::endl;
        }
    }
    Aws::ShutdownAPI(options);
}

