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
- **AWS C Library** [libs3](https://github.com/bji/libs3)

### Build
1. Install the AWS C Library
```
git clone https://github.com/bji/libs3
make -j
sudo make install
```

2. Clone this repository and navigate to the project directory:
```
git clone https://github.com/korea-dbs/sqlite-cloud-s3.git
cd sqlite-cloud-s3
```

3. Compile
```
mkdir bld && cd bld
cmake ..
make -j
```

## Run

First, you need to set THREE environment variable in the `bashrc`.

```
export S3_ACCESS_KEY_ID="YOUR-S3-KEY"
export S3_SECRET_ACCESS_KEY="sLtzO="YOUR-SECRET-S3-KEY"
export S3_HOSTNAME="s3-eu-north-1.amazonaws.com"
```

- Here, `s3-eu-north-1.amazonaws.com` is an example. Please check your bucket region.


Run the sqlite3-cloud-s3 
```
cd bld
./sqliet3-cloud-s3
```

## Contact

Jonghyeok Park jonghyeok_park@korea.ac.kr
Yewon Shin syw22@hufs.ac.kr
