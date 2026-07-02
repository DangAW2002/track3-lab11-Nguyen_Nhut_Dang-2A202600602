import os
import sqlite3

# Đường dẫn DB mặc định
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sqlite_lab.db")

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS courses;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    age INTEGER NOT NULL
);

CREATE TABLE courses (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE enrollments (
    student_id INTEGER NOT NULL,
    course_id TEXT NOT NULL,
    score REAL NOT NULL,
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
"""

SEED_SQL = """
INSERT INTO students (name, cohort, age) VALUES 
('Nguyen Nhut Dang', 'A1', 24),
('Tran Thi B', 'A1', 23),
('Le Van C', 'A2', 25),
('Pham Van D', 'A2', 22);

INSERT INTO courses (id, name, credits) VALUES 
('CS101', 'Introduction to Computer Science', 3),
('CS102', 'Data Structures and Algorithms', 4),
('CS201', 'Artificial Intelligence', 4);

INSERT INTO enrollments (student_id, course_id, score) VALUES 
(1, 'CS101', 90.0),
(1, 'CS102', 85.0),
(1, 'CS201', 95.0),
(2, 'CS101', 80.0),
(2, 'CS102', 75.0),
(3, 'CS101', 70.0),
(3, 'CS201', 88.0),
(4, 'CS102', 92.0),
(4, 'CS201', 81.0);
"""


def create_database(db_path=None):
    """
    Khởi tạo cơ sở dữ liệu SQLite tại db_path.
    Nếu db_path là None, sử dụng biến môi trường DB_PATH hoặc DEFAULT_DB_PATH.
    """
    if not db_path:
        db_path = os.getenv("DB_PATH", DEFAULT_DB_PATH)

    print(f"Khoi tao co so du lieu SQLite tai: {db_path}")

    # Đảm bảo thư mục cha tồn tại
    parent_dir = os.path.dirname(os.path.abspath(db_path))
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        # Chạy schema SQL
        cursor.executescript(SCHEMA_SQL)
        # Chạy seed SQL
        cursor.executescript(SEED_SQL)
        conn.commit()
        print("Khoi tao va seed du lieu thanh cong!")
    except Exception as e:
        conn.rollback()
        print(f"Loi khi khoi tao co so du lieu: {e}")
        raise e
    finally:
        conn.close()

    return db_path


if __name__ == "__main__":
    create_database()
