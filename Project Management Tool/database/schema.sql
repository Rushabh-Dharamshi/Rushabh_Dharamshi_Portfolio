CREATE TABLE IF NOT EXISTS projects (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO projects (name, description)
SELECT 'General', 'Default workspace for unassigned tasks'
WHERE NOT EXISTS (SELECT 1 FROM projects WHERE name = 'General');

CREATE TABLE IF NOT EXISTS tasks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  due_date DATE NOT NULL,
  priority ENUM('low', 'medium', 'high') NOT NULL,
  difficulty_level ENUM('easy', 'medium', 'hard') NOT NULL,
  progress INT NOT NULL CHECK (progress BETWEEN 0 AND 100),
  category VARCHAR(255),
  is_completed BOOLEAN DEFAULT false,
  project_id INT NULL,
  status ENUM('backlog', 'in_progress', 'blocked', 'done') NOT NULL DEFAULT 'backlog',
  assignee VARCHAR(255) NULL,
  estimated_hours DECIMAL(6,2) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

SET @project_id_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tasks'
    AND COLUMN_NAME = 'project_id'
);
SET @sql = IF(@project_id_exists = 0, 'ALTER TABLE tasks ADD COLUMN project_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @status_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tasks'
    AND COLUMN_NAME = 'status'
);
SET @sql = IF(
  @status_exists = 0,
  'ALTER TABLE tasks ADD COLUMN status ENUM(''backlog'', ''in_progress'', ''blocked'', ''done'') NOT NULL DEFAULT ''backlog''',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @assignee_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tasks'
    AND COLUMN_NAME = 'assignee'
);
SET @sql = IF(@assignee_exists = 0, 'ALTER TABLE tasks ADD COLUMN assignee VARCHAR(255) NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @estimated_hours_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tasks'
    AND COLUMN_NAME = 'estimated_hours'
);
SET @sql = IF(@estimated_hours_exists = 0, 'ALTER TABLE tasks ADD COLUMN estimated_hours DECIMAL(6,2) NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @created_at_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tasks'
    AND COLUMN_NAME = 'created_at'
);
SET @sql = IF(@created_at_exists = 0, 'ALTER TABLE tasks ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @updated_at_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tasks'
    AND COLUMN_NAME = 'updated_at'
);
SET @sql = IF(
  @updated_at_exists = 0,
  'ALTER TABLE tasks ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE tasks
SET status = CASE
  WHEN is_completed = 1 THEN 'done'
  WHEN progress >= 1 THEN 'in_progress'
  ELSE 'backlog'
END
WHERE status IS NULL OR status = '';

UPDATE tasks
SET project_id = (SELECT id FROM projects WHERE name = 'General' LIMIT 1)
WHERE project_id IS NULL;
