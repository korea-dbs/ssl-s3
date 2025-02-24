import sqlite3
import boto3
import os
import logging
import time
from botocore.exceptions import ClientError
from contextlib import closing

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# S3 클라이언트 설정
s3_client = boto3.client('s3')         
bucket_name = 'ku-general-test'
db_path = '/home/ids/ssd/tpcc_300.db'  # 데이터베이스 경로 수정
wal_file = db_path + '-wal'
shm_file = db_path + '-shm'
s3_wal_key = 'wal-file/sqlite.wal'

def download_from_s3(bucket, key, local_path):
    """S3에서 파일을 다운로드하는 함수"""
    start_time = time.time()
    try:
        s3_client.download_file(bucket, key, local_path)
        download_duration = time.time() - start_time
        logger.info(f"Successfully downloaded {key} from S3 bucket {bucket} to {local_path}")
        logger.info(f"S3 download time: {download_duration:.4f} seconds")
        return download_duration
    except ClientError as e:
        logger.error(f"Failed to download {key} from S3: {str(e)}")
        return None

def test_database_functionality(db_path):
    """데이터베이스 기본 기능 테스트"""
    try:
        with closing(sqlite3.connect(db_path)) as conn:  # closing 컨텍스트 매니저 사용
            cursor = conn.cursor()
            
            # 테이블 존재 여부 확인
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            if not tables:
                logger.warning("No tables found in the database")
                return False
            
            # 각 테이블에 대해 간단한 쿼리 수행
            for (table,) in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    logger.info(f"Table {table} has {count} rows")
                except sqlite3.Error as e:
                    logger.error(f"Error querying table {table}: {str(e)}")
                    return False
            
            logger.info("Database functionality test passed")
            return True
    except sqlite3.Error as e:
        logger.error(f"Database functionality test failed: {str(e)}")
        return False

def cleanup_wal_files(db_path):
    """WAL 및 SHM 파일을 정리하는 함수"""
    wal_path = db_path + '-wal'
    shm_path = db_path + '-shm'
    
    try:
        # WAL 파일 처리
        if os.path.exists(wal_path):
            os.remove(wal_path)
            logger.info(f"Removed WAL file: {wal_path}")
            
        # SHM 파일 처리
        if os.path.exists(shm_path):
            os.remove(shm_path)
            logger.info(f"Removed SHM file: {shm_path}")
            
        return True
    except OSError as e:
        logger.error(f"Failed to cleanup WAL/SHM files: {str(e)}")
        return False

def force_checkpoint(conn):
    """강제로 체크포인트를 수행하고 WAL 모드를 비활성화하는 함수"""
    try:
        # TRUNCATE 모드로 체크포인트 수행
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        
        # WAL 모드 비활성화
        conn.execute('PRAGMA journal_mode=DELETE')
        
        logger.info("Forced checkpoint completed and WAL mode disabled")
        return True
    except sqlite3.Error as e:
        logger.error(f"Failed to force checkpoint: {str(e)}")
        return False

def apply_wal_checkpoint(db_path, wal_path):
    """WAL 파일을 데이터베이스에 체크포인트하는 함수"""
    start_time = time.time()
    backup_path = wal_path + '.backup'
    
    try:
        # 데이터베이스 연결
        with closing(sqlite3.connect(db_path)) as conn:
            # 현재 WAL 파일이 있다면 백업
            if os.path.exists(wal_path):
                os.rename(wal_path, backup_path)
                logger.info(f"Existing WAL file backed up to {backup_path}")
            
            # S3에서 WAL 파일 다운로드
            download_time = download_from_s3(bucket_name, s3_wal_key, wal_path)
            
            if download_time is not None:
                # 체크포인트 수행 및 WAL 모드 비활성화
                checkpoint_start_time = time.time()
                if not force_checkpoint(conn):
                    raise Exception("Failed to perform checkpoint")
                checkpoint_duration = time.time() - checkpoint_start_time
                
                logger.info(f"Total operation time: {time.time() - start_time:.4f} seconds")
                logger.info(f"Checkpoint execution time: {checkpoint_duration:.4f} seconds")
                
                # WAL 및 SHM 파일 정리
                if not cleanup_wal_files(db_path):
                    raise Exception("Failed to cleanup WAL/SHM files")
                
                return True
            else:
                # 다운로드 실패 시 백업 복원
                if os.path.exists(backup_path):
                    os.rename(backup_path, wal_path)
                    logger.info("Restored original WAL file from backup")
                return False
                
    except sqlite3.Error as e:
        logger.error(f"SQLite error occurred: {str(e)}")
        if os.path.exists(backup_path):
            os.rename(backup_path, wal_path)
            logger.info("Restored original WAL file from backup due to error")
        return False
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}")
        return False
    finally:
        # 백업 파일 정리
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
                logger.info("Backup file cleaned up")
            except OSError as e:
                logger.error(f"Failed to clean up backup file: {str(e)}")

def verify_wal_cleanup(db_path):
    """WAL 및 SHM 파일이 정상적으로 제거되었는지 확인하는 함수"""
    wal_exists = os.path.exists(db_path + '-wal')
    shm_exists = os.path.exists(db_path + '-shm')
    
    if wal_exists or shm_exists:
        logger.error("WAL/SHM files still exist after cleanup")
        if wal_exists:
            logger.error(f"WAL file still exists: {db_path}-wal")
        if shm_exists:
            logger.error(f"SHM file still exists: {db_path}-shm")
        return False
    
    logger.info("WAL/SHM files successfully cleaned up")
    return True

def verify_database_integrity(db_path):
    """데이터베이스 무결성을 검증하는 함수"""
    try:
        with closing(sqlite3.connect(db_path)) as conn:  # closing 컨텍스트 매니저 사용
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            if result == "ok":
                logger.info("Database integrity check passed")
                return True
            else:
                logger.error(f"Database integrity check failed: {result}")
                return False
    except sqlite3.Error as e:
        logger.error(f"Failed to verify database integrity: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        # WAL 체크포인트 수행
        if apply_wal_checkpoint(db_path, wal_file):
            # WAL 파일 정리 확인
            if not verify_wal_cleanup(db_path):
                logger.error("Failed to clean up WAL/SHM files completely")
                
            # 데이터베이스 기능 테스트
            database_functional = test_database_functionality(db_path)
            
            # 데이터베이스 무결성 검증
            integrity_check = verify_database_integrity(db_path)
            
            # 최종 상태 로깅
            if database_functional and integrity_check:
                logger.info("Database is fully operational and intact")
            else:
                logger.error("Database functionality or integrity compromised")
                
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
