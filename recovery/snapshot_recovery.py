import sqlite3
import boto3
import os
import logging
import time
from botocore.exceptions import ClientError
from contextlib import closing

# logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# S3 client configuration
s3_client = boto3.client('s3')         
bucket_name = 'your-general-bucket-name'
db_path = 'your-db-path'
wal_file = db_path + '-wal'
shm_file = db_path + '-shm'
s3_wal_key = 'your-bucket-key'

def download_from_s3(bucket, key, local_path):
    """Function to download a file from S3"""
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
    """Test database basic functionality"""
    try:
        with closing(sqlite3.connect(db_path)) as conn:  # Use closing context manager
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            if not tables:
                logger.warning("No tables found in the database")
                return False
            
            # Perform simple queries on each table
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
    """Functions to clean up WAL and SHM files"""
    wal_path = db_path + '-wal'
    shm_path = db_path + '-shm'
    
    try:
        # Remove WAL file
        if os.path.exists(wal_path):
            os.remove(wal_path)
            logger.info(f"Removed WAL file: {wal_path}")
            
        # Remove SHM file
        if os.path.exists(shm_path):
            os.remove(shm_path)
            logger.info(f"Removed SHM file: {shm_path}")
            
        return True
    except OSError as e:
        logger.error(f"Failed to cleanup WAL/SHM files: {str(e)}")
        return False

def force_checkpoint(conn):
    """Function to force a checkpoint and disable WAL mode"""
    try:
        # Perform checkpointing in TRUNCATE mode
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        
        # Disable WAL mode
        conn.execute('PRAGMA journal_mode=DELETE')
        
        logger.info("Forced checkpoint completed and WAL mode disabled")
        return True
    except sqlite3.Error as e:
        logger.error(f"Failed to force checkpoint: {str(e)}")
        return False

def apply_wal_checkpoint(db_path, wal_path):
    """Function to checkpoint a WAL file into a database"""
    start_time = time.time()
    backup_path = wal_path + '.backup'
    
    try:
        # Connect database
        with closing(sqlite3.connect(db_path)) as conn:
            # Backup your current WAL file if you have it
            if os.path.exists(wal_path):
                os.rename(wal_path, backup_path)
                logger.info(f"Existing WAL file backed up to {backup_path}")
            
            # Download WAL file from S3
            download_time = download_from_s3(bucket_name, s3_wal_key, wal_path)
            
            if download_time is not None:
                # Perform checkpointing and disable WAL mode
                checkpoint_start_time = time.time()
                if not force_checkpoint(conn):
                    raise Exception("Failed to perform checkpoint")
                checkpoint_duration = time.time() - checkpoint_start_time
                
                logger.info(f"Total operation time: {time.time() - start_time:.4f} seconds")
                logger.info(f"Checkpoint execution time: {checkpoint_duration:.4f} seconds")
                
                # Clean up WAL and SHM files
                if not cleanup_wal_files(db_path):
                    raise Exception("Failed to cleanup WAL/SHM files")
                
                return True
            else:
                # Restore backup when download fails
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
        # Remove backup files
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
                logger.info("Backup file cleaned up")
            except OSError as e:
                logger.error(f"Failed to clean up backup file: {str(e)}")

def verify_wal_cleanup(db_path):
    """Function to check whether WAL and SHM files were removed properly"""
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
    """Function to verify database integrity"""
    try:
        with closing(sqlite3.connect(db_path)) as conn:  # Use closing context manager
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
        # Perform WAL checkpointing
        if apply_wal_checkpoint(db_path, wal_file):
            # Check WAL file cleanup
            if not verify_wal_cleanup(db_path):
                logger.error("Failed to clean up WAL/SHM files completely")
                
            # Database functional testing
            database_functional = test_database_functionality(db_path)
            
            # Database integrity verification
            integrity_check = verify_database_integrity(db_path)
            
            # Final status logging
            if database_functional and integrity_check:
                logger.info("Database is fully operational and intact")
            else:
                logger.error("Database functionality or integrity compromised")
                
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
