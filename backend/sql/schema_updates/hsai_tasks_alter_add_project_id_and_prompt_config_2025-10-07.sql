-- 扩展HSAI任务表结构，添加项目关联和提示词配置字段
ALTER TABLE hsai_tasks 
ADD COLUMN project_id VARCHAR REFERENCES hsai_projects(id),
ADD COLUMN prompt_config JSON;