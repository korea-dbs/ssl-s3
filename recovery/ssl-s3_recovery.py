import boto3
import sqlite3
import time
from datetime import datetime

def download_log_from_s3(bucket_name, file_key, local_path):
    """S3에서 로그 파일 다운로드"""
    try:
        start_time = time.time()
        s3_client = boto3.client('s3')
        s3_client.download_file(bucket_name, file_key, local_path)
        download_time = time.time() - start_time
        return download_time
    except Exception as e:
        print(f"S3 다운로드 중 오류 발생: {str(e)}")
        raise

def parse_sql_log(log_path):
    """SQL 로그 파일 파싱하여 개별 SQL 문장으로 분리"""
    sql_statements = []
    
    with open(log_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            statements = line.split(';')
            if statements[-1].strip() == '':
                statements = statements[:-1]
            
            for stmt in statements:
                if stmt.strip():
                    sql_statements.append(stmt.strip())
    
    return sql_statements

def execute_recovery(db_path, sql_statements):
    """SQL 문 실행하여 데이터베이스 복구"""
    conn = None
    try:
        start_time = time.time()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 복구 SQL 트랜잭션으로 실행
        cursor.execute("BEGIN TRANSACTION;")
        
        for sql in sql_statements:
            cursor.execute(sql)
        
        cursor.execute("COMMIT;")
        
        recovery_time = time.time() - start_time
        return conn, recovery_time
    except Exception as e:
        print(f"복구 중 오류 발생: {str(e)}")
        if conn:
            cursor.execute("ROLLBACK;")
        raise

def test_database(conn):
    """데이터베이스 복구 상태 테스트"""
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION;")
        
        test_queries = [
            "SELECT D_NEXT_O_ID FROM DISTRICT WHERE D_ID = 2 AND D_W_ID = 1",
            "SELECT * FROM ORDERS WHERE O_ID = 3001",
            "SELECT * FROM NEW_ORDER WHERE NO_O_ID = 3001",
            "SELECT S_QUANTITY FROM STOCK WHERE S_I_ID = 83024 AND S_W_ID = 1"
        ]
        
        all_results = []
        for query in test_queries:
            cursor.execute(query)
            all_results.append(cursor.fetchall())
        
        cursor.execute("COMMIT;")
        return all_results, True
    except Exception as e:
        print(f"테스트 중 오류 발생: {str(e)}")
        cursor.execute("ROLLBACK;")
        return None, False

def main():
    # 설정
    bucket_name = "ku-express-test--use1-az6--x-s3"
    file_key = "sql-file/sql.log"
    local_log_path = "downloaded_sql.log"
    db_path = "/home/ids/ssd/tpcc_300.db"
    
    try:
        # 다운로드 및 복구 수행
        download_time = download_log_from_s3(bucket_name, file_key, local_log_path)
        sql_statements = parse_sql_log(local_log_path)
        conn, recovery_time = execute_recovery(db_path, sql_statements)
        
        # 테스트 수행
        results, test_result = test_database(conn)
        
        # 최종 결과 출력
        print("\n=== 복구 작업 결과 ===")
        print(f"다운로드 시간: {download_time:.2f}초")
        print(f"복구 실행 시간: {recovery_time:.2f}초")
        print(f"총 소요 시간: {(download_time + recovery_time):.2f}초")
        print(f"복구 상태: {'성공' if test_result else '실패'}")
        
        conn.close()
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")

if __name__ == "__main__":
    main()
