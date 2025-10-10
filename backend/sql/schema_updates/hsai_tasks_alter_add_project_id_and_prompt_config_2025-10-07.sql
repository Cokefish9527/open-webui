-- 扩展任务表结构，添加项目关联字段和提示词配置字段
ALTER TABLE hsai_tasks 
ADD COLUMN project_id VARCHAR(255) REFERENCES hsai_projects(id);

ALTER TABLE hsai_tasks 
ADD COLUMN prompt_config JSON;