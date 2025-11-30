-- 禁用OpenAI数据源
-- 查看当前状态
SELECT id, name, type, url, enabled FROM sources WHERE name = 'OpenAI';

-- 禁用OpenAI
UPDATE sources SET enabled = false WHERE name = 'OpenAI';

-- 确认更新结果
SELECT id, name, type, url, enabled FROM sources WHERE name = 'OpenAI';
