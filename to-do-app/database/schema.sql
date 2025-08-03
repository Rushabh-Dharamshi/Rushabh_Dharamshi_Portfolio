CREATE TABLE IF NOT EXISTS tasks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  due_date DATE NOT NULL,
  priority ENUM('low', 'medium', 'high') NOT NULL,
  difficulty_level ENUM('easy', 'medium', 'hard') NOT NULL,
  progress INT NOT NULL CHECK (progress BETWEEN 0 AND 100),
  category VARCHAR(255),
  is_completed BOOLEAN DEFAULT false
);
