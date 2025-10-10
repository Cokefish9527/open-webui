-- 表 migratehistory 的结构
CREATE TABLE IF NOT EXISTS [migratehistory] (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    migrated_at DATETIME NOT NULL
);