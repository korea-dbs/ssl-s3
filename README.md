# SQLite-Cloud-S3


This project demonstrates an optimized technique for enhancing SQLite recovery efficiency by integrating with AWS S3. 
It provides mechanisms to upload Write-Ahead Logging (WAL) files and SQL statements to an S3 bucket in real-time whenever the WAL file is updated. 

## Features

- **Automatic WAL File Uploads**:  
  The project uses SQLite's `sqlite3_wal_hook` to detect changes in the WAL file and uploads the updated WAL file to a specified AWS S3 bucket.
  
- **SQL Statement Uploads**:  
  In addition to WAL file synchronization, this project also allows uploading SQL statements to an S3 bucket for further analysis or recovery purposes.

- **Seamless Integration with SQLite**:  
  The project is designed to work directly with SQLite, enabling transparent and efficient integration without modifying the core database engine.

## Getting Started

### Prerequisites
- **SQLite** (latest version from [SQLite GitHub Repository](https://github.com/sqlite/sqlite))
- **AWS SDK for C++** (for S3 integration)
- C++ compiler with SQLite and AWS SDK linked

### Build
1. Clone this repository and navigate to the project directory:
```
git clone https://github.com/korea-dbs/sqlite-cloud-s3.git
cd qlite-cloud-s3
```

2. Compile
```
mkdir bld && cd bld
cmake ..
make -j
```

## Run

First, you need to create `.env` file that contains your AWS account information
Create the `env` file and fill below information

```
cd src
vim .env
AWS_S3_BUCKET_NAME=YOUR-BUCKET-NAME
AWS_S3_KEY=YOUR-BUCKET-KEY
```

Run the sqlite3-cloud-s3 
```
cd bld
./sqliet3-cloud-s3
```

## Contact

Jonghyeok Park jonghyeok_park@korea.ac.kr
Yewon Shin syw22@hufs.ac.kr
