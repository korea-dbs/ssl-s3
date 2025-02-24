import sqlite3
import boto3
import os
import logging
import hashlib
import time
from botocore.exceptions import ClientError
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# S3 클라이언트 설정
s3_client = boto3.client('s3')
bucket_name = 'ku-express-test--use1-az6--x-s3'
bucket_key = 'wal-file/wal-partial.log'
db_path = '/home/ids/ssd/tpcc_300.db'
wal_file = db_path + '-wal'

def calculate_file_hash(file_path):
    """파일의 MD5 해시를 계산"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def verify_file_permissions(file_path):
    """파일 권한 확인 및 수정"""
    try:
        os.chmod(file_path, 0o644)
        return True
    except Exception as e:
        logger.error(f"Failed to set file permissions: {str(e)}")
        return False

def sync_file_to_disk(file_path):
    """파일을 디스크에 동기화"""
    try:
        with open(file_path, 'rb') as f:
            os.fsync(f.fileno())
        return True
    except Exception as e:
        logger.error(f"Failed to sync file to disk: {str(e)}")
        return False

def cleanup_db_files(db_path):
    """데이터베이스 관련 파일들(WAL, SHM) 정리"""
    try:
        # WAL 파일 정리
        wal_path = db_path + '-wal'
        if os.path.exists(wal_path):
            os.remove(wal_path)
            logger.info(f"Removed WAL file: {wal_path}")

        # SHM 파일 정리
        shm_path = db_path + '-shm'
        if os.path.exists(shm_path):
            os.remove(shm_path)
            logger.info(f"Removed SHM file: {shm_path}")

        return True
    except Exception as e:
        logger.error(f"Failed to cleanup database files: {str(e)}")
        return False

def download_from_s3(bucket, key, local_path):
    """S3에서 파일을 다운로드하고 무결성 검증"""
    download_start_time = time.time()
    try:
        # 파일 메타데이터 가져오기
        response = s3_client.head_object(Bucket=bucket, Key=key)
        s3_size = response['ContentLength']
        
        # 파일 다운로드
        s3_client.download_file(bucket, key, local_path)

        # 다운로드된 파일 크기 확인
        local_size = os.path.getsize(local_path)
        if local_size != s3_size:
            logger.error(f"File size mismatch. S3: {s3_size}, Local: {local_size}")
            return False, 0

        # 파일 권한 설정
        if not verify_file_permissions(local_path):
            return False, 0

        # 파일 동기화
        if not sync_file_to_disk(local_path):
            return False, 0

        # 다운로드 완료 후 잠시 대기
        time.sleep(1)

        download_time = time.time() - download_start_time
        logger.info(f"Successfully downloaded {key} from S3 bucket {bucket} to {local_path}")
        logger.info(f"Download time: {download_time:.2f} seconds")
        logger.info(f"File size: {s3_size / (1024*1024):.2f}MB")
        
        return True, download_time

    except ClientError as e:
        logger.error(f"Failed to download {key} from S3: {str(e)}")
        return False, 0

def test_database(db_path):
    """데이터베이스 동작 테스트"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 데이터베이스 읽기 테스트
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        if not tables:
            logger.warning("No tables found in database")
            return False
        
        # 2. 테스트 테이블 생성
        test_table = f"test_table_{int(time.time())}"
        cursor.execute(f"CREATE TABLE {test_table} (id INTEGER PRIMARY KEY, test_data TEXT)")
        
        # 3. 데이터 쓰기 테스트
        cursor.execute(f"INSERT INTO {test_table} (test_data) VALUES (?)", ("test_data",))
        
        # 4. 데이터 읽기 테스트
        cursor.execute(f"SELECT * FROM {test_table}")
        result = cursor.fetchone()
        
        # 5. 테스트 테이블 삭제
        cursor.execute(f"DROP TABLE {test_table}")
        
        conn.commit()
        
        if result and result[1] == "test_data":
            logger.info("Database functionality test passed successfully")
            return True
        else:
            logger.error("Database functionality test failed")
            return False
            
    except sqlite3.Error as e:
        logger.error(f"Database test failed: {str(e)}")
        return False
    finally:
        if conn:
            # WAL 모드 비활성화
            conn.execute('PRAGMA journal_mode=DELETE')
            conn.commit()
            conn.close()
            cleanup_db_files(db_path)

def apply_wal_checkpoint(db_path, wal_path):
    """WAL 파일을 데이터베이스에 체크포인트"""
    backup_path = wal_path + '.backup'
    download_time = 0
    checkpoint_start_time = 0
    checkpoint_time = 0
    conn = None
    
    try:
        if not os.path.exists(db_path):
            logger.error(f"Database file does not exist: {db_path}")
            return False, 0, 0
            
        if os.path.exists(wal_path):
            os.rename(wal_path, backup_path)
            logger.info(f"Existing WAL file backed up to {backup_path}")

        # S3에서 WAL 파일 다운로드 및 시간 측정
        download_success, download_time = download_from_s3(bucket_name, bucket_key, wal_path)
        
        if download_success:
            # 체크포인트 시작 시간 기록
            checkpoint_start_time = time.time()
            
            conn = sqlite3.connect(db_path, isolation_level=None)
            try:
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA synchronous=NORMAL')
                conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
                
                # 체크포인트 완료 시간 계산
                checkpoint_time = time.time() - checkpoint_start_time
                logger.info(f"Checkpoint completed successfully in {checkpoint_time:.2f} seconds")
                
                # WAL 모드 비활성화
                conn.execute('PRAGMA journal_mode=DELETE')
                conn.commit()
                
                # 데이터베이스 테스트 수행
                if not test_database(db_path):
                    logger.error("Database functionality test failed after checkpoint")
                    return False, download_time, checkpoint_time

                return True, download_time, checkpoint_time

            except sqlite3.Error as e:
                logger.error(f"SQLite error occurred: {str(e)}")
                return False, download_time, checkpoint_time
            finally:
                if conn:
                    conn.close()
                    cleanup_db_files(db_path)

        else:
            logger.error("Failed to download WAL file from S3")
            return False, download_time, 0

    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}")
        return False, download_time, checkpoint_time
    finally:
        if os.path.exists(backup_path):
            if not os.path.exists(wal_path):
                os.rename(backup_path, wal_path)
                logger.info("Restored original WAL file from backup")
            else:
                os.remove(backup_path)
                logger.info("Backup file cleaned up")
        
        # 최종 파일 정리 확인
        cleanup_db_files(db_path)

if __name__ == "__main__":
    try:
        logger.info("Starting WAL checkpoint process")
        
        success, download_time, checkpoint_time = apply_wal_checkpoint(db_path, wal_file)
        
        if success:
            logger.info("WAL checkpoint process completed successfully")
            logger.info(f"Performance metrics:")
            logger.info(f"- Download time: {download_time:.2f} seconds")
            logger.info(f"- Checkpoint time: {checkpoint_time:.2f} seconds")
            logger.info(f"- Total time: {(download_time + checkpoint_time):.2f} seconds")
        else:
            logger.error("WAL checkpoint process failed")
            
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
    finally:
        # 프로그램 종료 전 최종 파일 정리
        cleanup_db_files(db_path)
