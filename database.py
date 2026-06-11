"""
파일 메타데이터 저장 및 관리 시스템
SQLite 기반 데이터베이스
"""
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

DB_PATH = Path("files_db.sqlite")
JSON_DB_PATH = Path("files_db.json")

def get_connection():
    """SQLite 데이터베이스 연결"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 결과를 딕셔너리처럼 접근 가능하게 함
    return conn

def init_db():
    """데이터베이스 초기화 및 테이블 생성"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # files 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        uploaded_at TEXT NOT NULL,
        original_text TEXT NOT NULL,
        srt_text TEXT DEFAULT '',
        summaries TEXT DEFAULT '{}',
        last_updated TEXT
    )
    ''')

    cursor.execute("PRAGMA table_info(files)")
    columns = {row["name"] for row in cursor.fetchall()}
    if "srt_text" not in columns:
        cursor.execute("ALTER TABLE files ADD COLUMN srt_text TEXT DEFAULT ''")
    
    # 검색을 위한 인덱스 생성
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_filename ON files(filename)')
    
    conn.commit()
    
    # 기존 JSON 데이터가 있으면 마이그레이션 진행
    if JSON_DB_PATH.exists():
        migrate_from_json()
    
    conn.close()

def migrate_from_json():
    """기존 JSON 파일에서 SQLite로 데이터 이전"""
    try:
        with open(JSON_DB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            files = data.get("files", [])
            
            if not files:
                return
                
            conn = get_connection()
            cursor = conn.cursor()
            
            for file in files:
                # 이미 존재하는 ID인지 확인
                cursor.execute('SELECT id FROM files WHERE id = ?', (file["id"],))
                if cursor.fetchone():
                    continue
                    
                cursor.execute('''
                INSERT INTO files (id, filename, file_type, uploaded_at, original_text, summaries)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    file["id"],
                    file["filename"],
                    file.get("type", "unknown"),
                    file["uploaded_at"],
                    file["original_text"],
                    json.dumps(file.get("summaries", {}), ensure_ascii=False)
                ))
            
            conn.commit()
            conn.close()
            print(f"✓ {len(files)}개의 레코드가 JSON에서 SQLite로 성공적으로 이전되었습니다.")
            
            # 이전 후 JSON 파일 이름 변경 (백업)
            JSON_DB_PATH.rename(JSON_DB_PATH.with_suffix(".json.bak"))
    except Exception as e:
        print(f"마이그레이션 오류: {e}")

def create_file_record(filename: str, file_type: str, original_text: str, srt_text: str = "") -> Dict:
    """새 파일 레코드 생성"""
    file_id = str(uuid.uuid4())
    uploaded_at = datetime.now().isoformat()
    summaries = {}
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO files (id, filename, file_type, uploaded_at, original_text, srt_text, summaries)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (file_id, filename, file_type, uploaded_at, original_text, srt_text, json.dumps(summaries)))
    
    conn.commit()
    conn.close()
    
    return {
        "id": file_id,
        "filename": filename,
        "type": file_type,
        "uploaded_at": uploaded_at,
        "original_text": original_text,
        "srt_text": srt_text,
        "summaries": summaries
    }

def get_all_files() -> List[Dict]:
    """모든 파일 목록 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM files ORDER BY uploaded_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        item = dict(row)
        # JSON 문자열을 다시 딕셔너리로 변환
        item["summaries"] = json.loads(item["summaries"])
        # 필드명 호환성 (type <-> file_type)
        item["type"] = item["file_type"]
        results.append(item)
    return results

def get_file_by_id(file_id: str) -> Optional[Dict]:
    """ID로 파일 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM files WHERE id = ?', (file_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        item = dict(row)
        item["summaries"] = json.loads(item["summaries"])
        item["type"] = item["file_type"]
        return item
    return None

def update_summary(file_id: str, summary_type: str, summary_text: str) -> bool:
    """파일에 요약 추가/업데이트"""
    file = get_file_by_id(file_id)
    if not file:
        return False
    
    summaries = file["summaries"]
    summaries[summary_type] = summary_text
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    UPDATE files 
    SET summaries = ?, last_updated = ?
    WHERE id = ?
    ''', (json.dumps(summaries, ensure_ascii=False), datetime.now().isoformat(), file_id))
    
    conn.commit()
    conn.close()
    return True

def delete_summary(file_id: str, summary_type: str) -> bool:
    """파일의 특정 요약 삭제"""
    file = get_file_by_id(file_id)
    if not file:
        return False
    
    summaries = file["summaries"]
    if summary_type in summaries:
        del summaries[summary_type]
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE files 
        SET summaries = ?, last_updated = ?
        WHERE id = ?
        ''', (json.dumps(summaries, ensure_ascii=False), datetime.now().isoformat(), file_id))
        conn.commit()
        conn.close()
    return True

def delete_file(file_id: str) -> bool:
    """파일 삭제"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
    success = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    return success

def search_files(query: str) -> List[Dict]:
    """파일 검색"""
    conn = get_connection()
    cursor = conn.cursor()
    
    like_query = f"%{query}%"
    cursor.execute('''
    SELECT * FROM files 
    WHERE filename LIKE ? OR original_text LIKE ?
    ORDER BY uploaded_at DESC
    ''', (like_query, like_query))
    
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        item = dict(row)
        item["summaries"] = json.loads(item["summaries"])
        item["type"] = item["file_type"]
        results.append(item)
    return results

# 초기화
init_db()
