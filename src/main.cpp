#include <iostream>
#include "sqlite3.h"
#include "s3_wrapper.h"

#include <aws/core/Aws.h>
#include <aws/s3/S3Client.h>
#include <aws/s3/model/PutObjectRequest.h>

#include <iostream>
#include <fstream>
#include <string>
#include <cstdlib>

void loadEnv(const std::string& filename) {
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

int custom_wal_callback(void* pArg, sqlite3* db, const char* dbName, int walPages) {
    std::cout << "WAL callback triggered!" << std::endl;
    std::cout << "Database: " << dbName << ", WAL Pages: " << walPages << std::endl;

    const char* wal_file = sqlite3_db_filename(db, dbName);
    std::string wal_path = std::string(wal_file) + "-wal";
    std::cout << "WAL file path: " << wal_path << std::endl;

	s3_wrapper_example("hello stranger!");
    // 필요시 사용자 정의 로직 추가
    return SQLITE_OK;
}

int main() {
	// sqlite api integration example
    sqlite3 *db;
    int rc = sqlite3_open("./test.db", &db);

    if (rc) {
        std::cerr << "Can't open database: " << sqlite3_errmsg(db) << std::endl;
        return rc;
    } else {
        std::cout << "Opened database successfully!" << std::endl;
    }

	// register wal hook
	sqlite3_wal_hook(db, custom_wal_callback, nullptr);

	// set WAL mode
	const char* wal_mode_sql = "PRAGMA journal_mode=WAL;";
	char* err_msg = nullptr;
   	if (sqlite3_exec(db, wal_mode_sql, nullptr, nullptr, &err_msg) != SQLITE_OK) {
        std::cerr << "Failed to set WAL mode: " << err_msg << std::endl;
        sqlite3_free(err_msg);
        sqlite3_close(db);
        return 1;
    }

	// table creation
	const char* create_table_sql = "CREATE TABLE IF NOT EXISTS test (int num);";
    if (sqlite3_exec(db, create_table_sql, nullptr, nullptr, &err_msg) != SQLITE_OK) {
        std::cerr << "Failed to create table: " << err_msg << std::endl;
        sqlite3_free(err_msg);
        sqlite3_close(db);
        return 1;
    }

	// populate the database
	const char* insert_sql = "INSERT INTO test values(1);";
    if (sqlite3_exec(db, insert_sql, nullptr, nullptr, &err_msg) != SQLITE_OK) {
        std::cerr << "Failed to insert data: " << err_msg << std::endl;
        sqlite3_free(err_msg);
        sqlite3_close(db);
        return 1;
    }

	// invoke checkpoint explicitly (if neeeded)
	const char* checkpoint_sql = "PRAGMA wal_checkpoint(FULL);";
    if (sqlite3_exec(db, checkpoint_sql, nullptr, nullptr, &err_msg) != SQLITE_OK) {
        std::cerr << "Failed to perform checkpoint: " << err_msg << std::endl;
        sqlite3_free(err_msg);
        sqlite3_close(db);
        return 1;
    }
	
    sqlite3_close(db);

	// aws api integration example
	loadEnv("../src/.env");
    const char* bucketName = std::getenv("AWS_S3_BUCKET_NAME");
    const char* s3Key = std::getenv("AWS_S3_KEY");
    std::cout << "Bucket Name: " << bucketName << std::endl;
    std::cout << "S3 Key: " << s3Key << std::endl;

   	Aws::SDKOptions options;
    Aws::InitAPI(options);
    {
    	std::cout << "init API\n";    
	}
    Aws::ShutdownAPI(options);

    return 0;
}

