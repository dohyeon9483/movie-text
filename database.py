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
        corrected_srt_text TEXT DEFAULT '',
        english_srt_text TEXT DEFAULT '',
        media_path TEXT DEFAULT '',
        thumbnail_path TEXT DEFAULT '',
        summaries TEXT DEFAULT '{}',
        last_updated TEXT
    )
    ''')

    cursor.execute("PRAGMA table_info(files)")
    columns = {row["name"] for row in cursor.fetchall()}
    if "srt_text" not in columns:
        cursor.execute("ALTER TABLE files ADD COLUMN srt_text TEXT DEFAULT ''")
    if "corrected_srt_text" not in columns:
        cursor.execute("ALTER TABLE files ADD COLUMN corrected_srt_text TEXT DEFAULT ''")
    if "english_srt_text" not in columns:
        cursor.execute("ALTER TABLE files ADD COLUMN english_srt_text TEXT DEFAULT ''")
    if "media_path" not in columns:
        cursor.execute("ALTER TABLE files ADD COLUMN media_path TEXT DEFAULT ''")
    if "thumbnail_path" not in columns:
        cursor.execute("ALTER TABLE files ADD COLUMN thumbnail_path TEXT DEFAULT ''")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS artifacts (
        id TEXT PRIMARY KEY,
        file_id TEXT,
        kind TEXT NOT NULL,
        language TEXT NOT NULL,
        path TEXT NOT NULL,
        filename TEXT NOT NULL,
        created_at TEXT NOT NULL,
        metadata TEXT DEFAULT '{}',
        FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        file_id TEXT,
        job_type TEXT NOT NULL,
        status TEXT NOT NULL,
        progress INTEGER DEFAULT 0,
        message TEXT DEFAULT '',
        result_artifact_id TEXT,
        error TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        metadata TEXT DEFAULT '{}',
        FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
    )
    ''')
    
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
                INSERT INTO files (id, filename, file_type, uploaded_at, original_text, summaries, srt_text, english_srt_text, media_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file["id"],
                    file["filename"],
                    file.get("type", "unknown"),
                    file["uploaded_at"],
                    file["original_text"],
                    json.dumps(file.get("summaries", {}), ensure_ascii=False),
                    file.get("srt_text", ""),
                    file.get("english_srt_text", ""),
                    file.get("media_path", "")
                ))
            
            conn.commit()
            conn.close()
            print(f"✓ {len(files)}개의 레코드가 JSON에서 SQLite로 성공적으로 이전되었습니다.")
            
            # 이전 후 JSON 파일 이름 변경 (백업)
            JSON_DB_PATH.rename(JSON_DB_PATH.with_suffix(".json.bak"))
    except Exception as e:
        print(f"마이그레이션 오류: {e}")

def create_file_record(
    filename: str,
    file_type: str,
    original_text: str,
    srt_text: str = "",
    media_path: str = "",
    english_srt_text: str = "",
    corrected_srt_text: str = "",
    thumbnail_path: str = "",
) -> Dict:
    """새 파일 레코드 생성"""
    file_id = str(uuid.uuid4())
    uploaded_at = datetime.now().isoformat()
    summaries = {}
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO files (id, filename, file_type, uploaded_at, original_text, srt_text, corrected_srt_text, english_srt_text, media_path, thumbnail_path, summaries)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (file_id, filename, file_type, uploaded_at, original_text, srt_text, corrected_srt_text, english_srt_text, media_path, thumbnail_path, json.dumps(summaries)))
    
    conn.commit()
    conn.close()
    
    return {
        "id": file_id,
        "filename": filename,
        "type": file_type,
        "uploaded_at": uploaded_at,
        "original_text": original_text,
        "srt_text": srt_text,
        "corrected_srt_text": corrected_srt_text,
        "english_srt_text": english_srt_text,
        "media_path": media_path,
        "thumbnail_path": thumbnail_path,
        "summaries": summaries
    }

def update_file_fields(file_id: str, **fields) -> bool:
    allowed = {"srt_text", "corrected_srt_text", "english_srt_text", "media_path", "thumbnail_path", "original_text"}
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return False
    updates["last_updated"] = datetime.now().isoformat()
    assignments = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [file_id]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE files SET {assignments} WHERE id = ?", values)
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def update_english_srt(file_id: str, english_srt_text: str) -> bool:
    return update_file_fields(file_id, english_srt_text=english_srt_text)

def create_artifact(file_id: Optional[str], kind: str, language: str, path: str, filename: str, metadata: Optional[Dict] = None) -> Dict:
    artifact_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    metadata = metadata or {}
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO artifacts (id, file_id, kind, language, path, filename, created_at, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (artifact_id, file_id, kind, language, path, filename, created_at, json.dumps(metadata, ensure_ascii=False)))
    conn.commit()
    conn.close()
    return {
        "id": artifact_id,
        "file_id": file_id,
        "kind": kind,
        "language": language,
        "path": path,
        "filename": filename,
        "created_at": created_at,
        "metadata": metadata
    }

def get_artifact_by_id(artifact_id: str) -> Optional[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM artifacts WHERE id = ?', (artifact_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    item = dict(row)
    item["metadata"] = json.loads(item.get("metadata") or "{}")
    return item

def get_artifacts_for_file(file_id: str) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM artifacts WHERE file_id = ? ORDER BY created_at DESC', (file_id,))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        item = dict(row)
        item["metadata"] = json.loads(item.get("metadata") or "{}")
        results.append(item)
    return results

def attach_artifact_summary(file: Dict) -> Dict:
    artifacts = get_artifacts_for_file(file["id"])
    file["artifacts"] = artifacts
    file["artifact_summary"] = {
        "audio_ko": any(item["kind"] == "audio" and item["language"] == "ko" for item in artifacts),
        "audio_en": any(item["kind"] == "audio" and item["language"] == "en" for item in artifacts),
        "video_ko": any(item["kind"] == "video" and item["language"] == "ko" for item in artifacts),
        "video_en": any(item["kind"] == "video" and item["language"] == "en" for item in artifacts),
        "subtitle_video_ko": any(item["kind"] == "subtitle_video" and item["language"] == "ko" for item in artifacts),
        "subtitle_video_en": any(item["kind"] == "subtitle_video" and item["language"] == "en" for item in artifacts),
        "captioned_dub_video_ko": any(item["kind"] == "captioned_dub_video" and item["language"] == "ko" for item in artifacts),
        "captioned_dub_video_en": any(item["kind"] == "captioned_dub_video" and item["language"] == "en" for item in artifacts),
    }
    return file

def create_job(file_id: Optional[str], job_type: str, metadata: Optional[Dict] = None) -> Dict:
    job_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    metadata = metadata or {}
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO jobs (id, file_id, job_type, status, progress, message, created_at, updated_at, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (job_id, file_id, job_type, "pending", 0, "대기 중", now, now, json.dumps(metadata, ensure_ascii=False)))
    conn.commit()
    conn.close()
    return get_job_by_id(job_id)

def update_job(job_id: str, **fields) -> bool:
    allowed = {"status", "progress", "message", "result_artifact_id", "error", "metadata"}
    updates = {key: value for key, value in fields.items() if key in allowed}
    if "metadata" in updates:
        updates["metadata"] = json.dumps(updates["metadata"], ensure_ascii=False)
    updates["updated_at"] = datetime.now().isoformat()
    assignments = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [job_id]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", values)
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def _job_from_row(row) -> Dict:
    item = dict(row)
    item["metadata"] = json.loads(item.get("metadata") or "{}")
    return item

def get_job_by_id(job_id: str) -> Optional[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
    row = cursor.fetchone()
    conn.close()
    return _job_from_row(row) if row else None

def get_jobs(file_id: Optional[str] = None) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    if file_id:
        cursor.execute('SELECT * FROM jobs WHERE file_id = ? ORDER BY created_at DESC', (file_id,))
    else:
        cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [_job_from_row(row) for row in rows]

def attach_job_summary(file: Dict) -> Dict:
    jobs = get_jobs(file["id"])
    file["jobs"] = jobs[:5]
    active = next((job for job in jobs if job["status"] in {"pending", "running"}), None)
    latest = jobs[0] if jobs else None
    file["job_summary"] = {
        "active": active,
        "latest": latest,
        "status": (active or latest or {}).get("status", "idle"),
        "progress": (active or latest or {}).get("progress", 0),
        "message": (active or latest or {}).get("message", "대기 중"),
    }
    return file

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
        attach_artifact_summary(item)
        attach_job_summary(item)
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
        attach_artifact_summary(item)
        attach_job_summary(item)
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
        attach_artifact_summary(item)
        attach_job_summary(item)
        results.append(item)
    return results

# 초기화
init_db()
