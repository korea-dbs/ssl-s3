# SQLite-Cloud-S3


This project demonstrates an optimized technique for enhancing SQLite recovery efficiency by integrating with AWS S3. 
It provides mechanisms to upload Write-Ahead Logging (WAL) files and SQL statements to an S3 bucket in real-time whenever the WAL file is updated. 
It also provides a recovery mechanism that downloads wal files/sql logs from s3 bucket and performs checkpoint or re-executes sql.

## Features

- **Automatic WAL File Uploads**:  
  The project uses SQLite's `sqlite3_wal_hook` to detect changes in the WAL file and uploads the updated WAL file to a specified AWS S3 bucket.
  
- **SQL Statement Uploads**:  
  In addition to WAL file synchronization, this project also allows uploading SQL statements to an S3 bucket for further analysis or recovery purposes.

- **Seamless Integration with SQLite**:  
  The project is designed to work directly with SQLite, enabling transparent and efficient integration without modifying the core database engine.

- **Recovery Script with WAL**:  
  A specialized Python script for downloading WAL files from different AWS storage options and applying checkpoints.

- **Recovery Script with SQL Statement**:  
  A Python script that downloads SQL logs from S3 and executes them to recover database state.

## Getting Started

### Prerequisites
- **SQLite** (latest version from [SQLite GitHub Repository](https://github.com/sqlite/sqlite))
- **Python** (Python 3.8.10 [Python Download Link](https://www.python.org/downloads/release/python-3810/))
- **AWS C Library** [libs3](https://github.com/bji/libs3)
- **boto3 Library** [boto3](https://github.com/boto/boto3)

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

3. Configure
```
mkdir bld && cd bld
../src/configure
```

4. Select Mode
```
vi Makefile
```
Change the -DAWS_S3_RECV value in Makefile. The upload mode corresponding to each number is as follows:
- 1: Upload entire WAL files (general bucket)
- 2: WAL file partial upload (express bucket)
- 3: Upload SQL file (express bucket)
```
CC = gcc
CFLAGS =   -g -O2 -DSQLITE_OS_UNIX=1 -DAWS_S3_RECV=2
```

5. Please modify bucket_name and bucket_key to suit your environment.
```
cd ../src/src
vi wal.c
```
In the 'sqlite3WalCallback' function, find and modify the sprintf statement that looks like the example below that operates in the selected mode.
```
sprintf(command, "aws s3api put-object --bucket <your-bucket-name> --key <your-bucket-key> --body \"%s\" > /dev/null", pWal->zWalName); 
```

6. Compile
```
cd ../../bld
make clean && make -j
sudo make install -j
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

If you perform it repeatedly, you must go into the s3 bucket, delete the files, and perform a new operation.

## Recovery

Install the boto3 Library
```
pip2 install boto3
```

Modify three variables in the python script file to suit your environment.
```
bucket_name="your_bucket_name"
bucket_key="path_in_the_bucket"
db_path="path_to_your_database"
```

Run the Python script
```
python xxx_recovery.py
```
- Here, `xxx_recovery.py` is an example. Select the Python file you want to run.


## Contact

Jonghyeok Park jonghyeok_park@korea.ac.kr  
Yewon Shin syw22@hufs.ac.kr
