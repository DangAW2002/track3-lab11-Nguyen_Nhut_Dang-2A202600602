import os
import sys
import tempfile
import pytest

# Them thu muc cha vao sys.path de import duoc db va mcp_server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from init_db import create_database
from db import SQLiteAdapter, ValidationError
from mcp_server import search, insert, aggregate, database_schema, table_schema


@pytest.fixture
def temp_db():
    """Tạo một database SQLite tạm thời cho mỗi test case."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    create_database(path)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture
def adapter(temp_db):
    """Cung cấp SQLiteAdapter kết nối tới DB tạm."""
    return SQLiteAdapter(temp_db)


def test_db_initialization(temp_db, adapter):
    """Kiểm tra việc khởi tạo DB và các bảng."""
    tables = adapter.list_tables()
    assert set(tables) == {"students", "courses", "enrollments"}

    # Kiểm tra số lượng dòng ban đầu
    students = adapter.search("students")
    assert len(students) == 4

    courses = adapter.search("courses")
    assert len(courses) == 3

    enrollments = adapter.search("enrollments")
    assert len(enrollments) == 9


def test_adapter_search(adapter):
    """Kiểm tra tìm kiếm và các bộ lọc."""
    # Tìm học sinh lớp A1
    res = adapter.search("students", filters=[{"column": "cohort", "operator": "=", "value": "A1"}])
    assert len(res) == 2
    assert {r["name"] for r in res} == {"Nguyen Nhut Dang", "Tran Thi B"}

    # Chỉ định các cột cần lấy
    res_cols = adapter.search("students", columns=["name", "cohort"], limit=1)
    assert len(res_cols) == 1
    assert set(res_cols[0].keys()) == {"name", "cohort"}

    # Lọc lớn hơn / nhỏ hơn
    res_age = adapter.search("students", filters=[{"column": "age", "operator": ">", "value": 23}])
    assert len(res_age) == 2  # Nhut Dang (24) va Le Van C (25)

    # Sap xep va phan trang
    res_sort = adapter.search("students", order_by="age", descending=True, limit=2)
    assert res_sort[0]["age"] == 25
    assert res_sort[1]["age"] == 24


def test_adapter_search_in_operator(adapter):
    """Kiểm tra toán tử IN."""
    res = adapter.search("students", filters=[{"column": "cohort", "operator": "IN", "value": ["A1", "A3"]}])
    assert len(res) == 2

    # Lỗi nếu IN truyền chuỗi thay vì list
    with pytest.raises(ValidationError):
        adapter.search("students", filters=[{"column": "cohort", "operator": "IN", "value": "A1"}])


def test_adapter_insert(adapter):
    """Kiểm tra chèn dữ liệu mới."""
    new_std = {"name": "Test Student", "cohort": "A3", "age": 20}
    res = adapter.insert("students", new_std)
    assert res["id"] is not None
    assert res["name"] == "Test Student"

    # Kiểm tra lỗi trùng lặp khóa chính cho courses
    new_course = {"id": "CS101", "name": "Duplicate Course", "credits": 3}
    with pytest.raises(ValidationError):
        adapter.insert("courses", new_course)

    # Kiểm tra lỗi khóa ngoại không tồn tại trong enrollments
    bad_enroll = {"student_id": 999, "course_id": "CS101", "score": 80.0}
    with pytest.raises(ValidationError):
        adapter.insert("enrollments", bad_enroll)


def test_adapter_aggregate(adapter):
    """Kiểm tra các hàm gom nhóm."""
    # COUNT
    count_res = adapter.aggregate("students", "COUNT")
    assert count_res[0]["value"] == 4

    avg_res = adapter.aggregate("enrollments", "AVG", "score")
    assert avg_res[0]["value"] == 84.0  # (90+85+95+80+75+70+88+92+81)/9 = 756/9 = 84.0

    # AVG score group by course_id
    group_res = adapter.aggregate("enrollments", "AVG", "score", group_by="course_id")
    assert len(group_res) == 3
    # Check score CS101: (90+80+70)/3 = 80.0
    cs101_score = next(r for r in group_res if r["course_id"] == "CS101")
    assert cs101_score["value"] == 80.0


def test_adapter_validation_errors(adapter):
    """Kiểm tra hệ thống validation ngăn chặn truy vấn bậy."""
    with pytest.raises(ValidationError):
        adapter.search("fake_table")

    with pytest.raises(ValidationError):
        adapter.search("students", columns=["fake_col"])

    with pytest.raises(ValidationError):
        adapter.search("students", filters=[{"column": "name", "operator": "INJECT", "value": "a"}])

    with pytest.raises(ValidationError):
        adapter.aggregate("students", "DROP")


# --- Test cac cong cu MCP (mcp_server.py) ---

def test_mcp_tools(temp_db):
    """Kiểm tra trực tiếp các decorator functions của mcp_server.py."""
    # Set DB_PATH về temp_db
    os.environ["DB_PATH"] = temp_db
    # Khoi tao lai adapter cua mcp_server bang cach reload hoac cap nhat lai db_path
    import mcp_server
    mcp_server.adapter = SQLiteAdapter(temp_db)

    # Test search tool
    res_str = mcp_server.search("students", filters=[{"column": "cohort", "operator": "=", "value": "A1"}])
    import json
    res = json.loads(res_str)
    assert len(res) == 2

    # Test insert tool
    insert_str = mcp_server.insert("students", {"name": "Bobby", "cohort": "A2", "age": 22})
    insert_res = json.loads(insert_str)
    assert insert_res["status"] == "success"
    assert insert_res["data"]["name"] == "Bobby"

    # Test aggregate tool
    agg_str = mcp_server.aggregate("students", "COUNT")
    agg_res = json.loads(agg_str)
    assert agg_res[0]["value"] == 5  # 4 seed + 1 insert o tren

    # Test database_schema resource
    db_schema_str = mcp_server.database_schema()
    schema = json.loads(db_schema_str)
    assert "students" in schema
    assert "courses" in schema
    assert "enrollments" in schema

    # Test table_schema resource
    table_schema_str = mcp_server.table_schema("students")
    tbl_schema = json.loads(table_schema_str)
    assert "students" in tbl_schema
    assert len(tbl_schema["students"]) == 4

    # Don dep env
    del os.environ["DB_PATH"]
