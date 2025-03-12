import sqlite3
import os
import json
import logging
from typing import Dict, List, Any

class DatabaseManager:
    """数据库管理器

    用于将爬取的作业数据保存到SQLite数据库中。
    """

    def __init__(self, db_path=None):
        """初始化数据库管理器

        Args:
            db_path: 数据库文件路径，默认为当前目录下的homework.db
        """
        if db_path is None:
            db_path = os.path.join(os.getcwd(), "homework.db")
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._init_tables()
        logging.info(f"数据库已连接: {db_path}")

    def _init_tables(self):
        """初始化数据库表结构"""
        # 创建课程表
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT NOT NULL,
            course_url TEXT NOT NULL UNIQUE
        )
        """)

        # 创建作业表
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS homework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            homework_name TEXT NOT NULL,
            homework_url TEXT NOT NULL UNIQUE,
            save_path TEXT NOT NULL,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
        """)

        # 创建学生作业表
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_homework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            homework_id INTEGER NOT NULL,
            student_name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            answer TEXT NOT NULL,
            score REAL,
            FOREIGN KEY (homework_id) REFERENCES homework(id),
            UNIQUE(homework_id, student_id)
        )
        """)

        self.conn.commit()

    def save_homework_data(self, task: Dict[str, Any], results: List[Dict[str, Any]]):
        """保存作业数据到数据库

        Args:
            task: 任务信息，包含课程名称、作业名称、作业URL等
            results: 处理后的结果数据，包含学生作业信息
        """
        try:
            # 提取课程信息
            course_name = task.get("课程名称", "未知课程")
            course_url = task.get("课程链接", "")
            
            # 提取作业信息
            homework_name = task.get("作业名称", "未知作业")
            homework_url = task.get("作业批阅链接", "")
            save_path = task.get("save_path", "")
            
            # 插入或获取课程ID
            self.cursor.execute(
                "INSERT OR IGNORE INTO courses (course_name, course_url) VALUES (?, ?)",
                (course_name, course_url)
            )
            self.cursor.execute(
                "SELECT id FROM courses WHERE course_url = ?", 
                (course_url,)
            )
            course_id = self.cursor.fetchone()[0]
            
            # 插入或获取作业ID
            self.cursor.execute(
                "INSERT OR IGNORE INTO homework (course_id, homework_name, homework_url, save_path) VALUES (?, ?, ?, ?)",
                (course_id, homework_name, homework_url, save_path)
            )
            self.cursor.execute(
                "SELECT id FROM homework WHERE homework_url = ?", 
                (homework_url,)
            )
            homework_id = self.cursor.fetchone()[0]
            
            # 插入学生作业数据
            for result in results:
                student_name = result.get("姓名", "未知学生")
                student_id = result.get("学号", "")
                answer = json.dumps(result, ensure_ascii=False)
                
                self.cursor.execute(
                    "INSERT OR REPLACE INTO student_homework (homework_id, student_name, student_id, answer, score) VALUES (?, ?, ?, ?, ?)",
                    (homework_id, student_name, student_id, answer, None)
                )
            
            self.conn.commit()
            logging.info(f"成功保存作业数据到数据库: {homework_name}")
            
        except Exception as e:
            self.conn.rollback()
            logging.error(f"保存作业数据到数据库失败: {str(e)}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logging.info("数据库连接已关闭")