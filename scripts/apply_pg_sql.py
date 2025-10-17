import os
import sys
import psycopg2


def load_database_url(env_path='.env'):
    if not os.path.exists(env_path):
        raise RuntimeError('.env not found')
    db_url = None
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('DATABASE_URL='):
                db_url = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
                break
    if not db_url:
        raise RuntimeError('DATABASE_URL not found in .env')
    if db_url.startswith('postgres://'):
        db_url = 'postgresql://' + db_url[len('postgres://'):]
    return db_url


def apply_files(conn, files, db_schema=None):
    ok, failed = [], []
    with conn:
        with conn.cursor() as cur:
            # Optional schema handling
            if db_schema and db_schema.lower() not in ('public', ''):
                try:
                    cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{db_schema}";')
                    cur.execute(f'SET search_path TO "{db_schema}", public;')
                except Exception as e:
                    conn.rollback()
                    raise

            for path in files:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        sql = f.read()
                    cur.execute('BEGIN;')
                    cur.execute(sql)
                    cur.execute('COMMIT;')
                    ok.append(path)
                except Exception as e:
                    conn.rollback()
                    failed.append((path, str(e)))
    return ok, failed


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    os.chdir(repo_root)

    db_url = load_database_url()
    files = [
        # 基础表（幂等）
        'backend/sql/postgres/init/2025-10-17_pg_companies.sql',
        'backend/sql/postgres/init/2025-10-17_pg_hsai_tasks.sql',
        'backend/sql/postgres/init/2025-10-17_pg_redis_queue_messages.sql',
        # 迁移（确保旧表补齐列）
        'backend/sql/schema_updates/2025-10-17_redis_queue_messages_add_correlation_id.sql',
        'backend/sql/schema_updates/2025-10-17_hsai_projects_add_organization_id.sql',
        # 项目表（无组织索引依赖）
        'backend/sql/postgres/init/2025-10-17_pg_hsai_projects.sql',
        # 后续索引增强
        'backend/sql/schema_updates/2025-10-17_hsai_projects_add_index_user_org.sql',
    ]
    files = [f for f in files if os.path.exists(f)]
    if not files:
        print('[WARN] No SQL files found to apply')
        return 0

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
    except Exception as e:
        print('[ERROR] Failed to connect to PostgreSQL:', str(e), file=sys.stderr)
        return 3

    db_schema = os.environ.get('DATABASE_SCHEMA', '').strip()
    ok, failed = apply_files(conn, files, db_schema=db_schema)

    print('=== DB Update Summary ===')
    print('Applied OK:', len(ok))
    for p in ok:
        print('  -', p)
    if failed:
        print('Failed:', len(failed))
        for p, err in failed:
            print('  -', p, '->', err)
        return 5
    return 0


if __name__ == '__main__':
    sys.exit(main())
