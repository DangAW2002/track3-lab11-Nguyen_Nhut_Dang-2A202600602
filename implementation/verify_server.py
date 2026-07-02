import json
from init_db import create_database
from db import SQLiteAdapter, ValidationError


def main():
    print("=== BAT DAU KIEM TRA ADAPTER DATABSE ===")

    # 1. Khoi tao lai co so du lieu
    db_path = create_database()
    adapter = SQLiteAdapter(db_path)

    # 2. Test list_tables
    tables = adapter.list_tables()
    print(f"\n[1] Danh sach bang trong database: {tables}")
    assert set(tables) == {"students", "courses", "enrollments"}, "Loi: Khong lay dung danh sach bang!"

    # 3. Test get_table_schema
    schema_students = adapter.get_table_schema("students")
    print(f"\n[2] Schema bang 'students':\n{json.dumps(schema_students, indent=2)}")

    # 4. Test search: lay tat ca hoc sinh cohort 'A1'
    filters_search = [{"column": "cohort", "operator": "=", "value": "A1"}]
    students_a1 = adapter.search("students", filters=filters_search)
    print(f"\n[3] Sinh vien thuoc cohort A1:\n{json.dumps(students_a1, indent=2)}")
    assert len(students_a1) == 2, f"Loi: Mong muon 2 sinh vien A1, nhung thay {len(students_a1)}"

    # 5. Test search voi IN operator
    filters_in = [{"column": "id", "operator": "IN", "value": [1, 3]}]
    students_in = adapter.search("students", filters=filters_in)
    print(f"\n[4] Sinh vien co ID trong [1, 3]:\n{json.dumps(students_in, indent=2)}")
    assert len(students_in) == 2, f"Loi: Mong muon 2 sinh vien, nhung thay {len(students_in)}"

    # 6. Test insert: chen 1 sinh vien moi
    new_student = {"name": "Gia Huy", "cohort": "A1", "age": 21}
    inserted = adapter.insert("students", new_student)
    print(f"\n[5] Ket qua chen sinh vien moi:\n{json.dumps(inserted, indent=2)}")
    assert inserted["id"] is not None, "Loi: Chen sinh vien nhung id rong!"
    assert inserted["name"] == "Gia Huy", "Loi: Thong tin chen khong khop!"

    # 7. Test aggregate: dem so sinh vien
    total_students = adapter.aggregate("students", "COUNT")
    print(f"\n[6] Dem so sinh vien: {total_students}")
    assert total_students[0]["value"] == 5, f"Loi: Mong muon 5 sinh vien, nhung thay {total_students[0]['value']}"

    # 8. Test aggregate voi group_by: diem trung binh theo khoa hoc
    avg_scores = adapter.aggregate("enrollments", "AVG", "score", group_by="course_id")
    print(f"\n[7] Diem trung binh theo tung khoa hoc:\n{json.dumps(avg_scores, indent=2)}")

    # 9. Kiem tra tinh nang an toan (Security/Validation tests)
    print("\n[8] Kiem tra tu choi cac truy van khong an toan:")

    # 9.1 Bang khong ton tai
    try:
        adapter.search("fake_table")
        print("    -> FAIL: Khong bi chan khi search bang gia!")
    except ValidationError as ve:
        print(f"    -> OK (Chan search bang gia): {ve}")

    # 9.2 Cot khong ton tai
    try:
        adapter.search("students", filters=[{"column": "fake_column", "operator": "=", "value": 1}])
        print("    -> FAIL: Khong bi chan khi loc bang cot gia!")
    except ValidationError as ve:
        print(f"    -> OK (Chan loc bang cot gia): {ve}")

    # 9.3 Toan tu khong ho tro (Sql injection attempt)
    try:
        adapter.search("students", filters=[{"column": "cohort", "operator": "= 'A1' OR 1=1;--", "value": ""}])
        print("    -> FAIL: Khong bi chan khi su dung toan tu la!")
    except ValidationError as ve:
        print(f"    -> OK (Chan toan tu la): {ve}")

    # 9.4 Aggregate metric la
    try:
        adapter.aggregate("students", "DELETE")
        print("    -> FAIL: Khong bi chan khi su dung aggregate metric la!")
    except ValidationError as ve:
        print(f"    -> OK (Chan aggregate metric la): {ve}")

    print("\n=== HOAN THANH KIEM TRA ADAPTER DATABSE (TAT CA DEU OK) ===")


if __name__ == "__main__":
    main()
