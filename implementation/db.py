import os
import sqlite3
from typing import List, Dict, Any, Optional


class ValidationError(ValueError):
    """Loi do du lieu yeu cau khong hop le hoac khong an toan."""
    pass


class SQLiteAdapter:
    """
    Adapter an toan cho SQLite.
    Thuc hien validate nghiem ngat truoc khi thuc thi SQL de tranh SQL Injection.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.getenv(
                "DB_PATH",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "sqlite_lab.db")
            )
        self.db_path = db_path

        # Danh sach trang (allowlist) cac bang va cot hop le
        self.schema_allowlist = {
            "students": {"id", "name", "cohort", "age"},
            "courses": {"id", "name", "credits"},
            "enrollments": {"student_id", "course_id", "score"}
        }

        self.allowed_operators = {"=", "!=", ">", "<", ">=", "<=", "LIKE", "IN"}
        self.allowed_metrics = {"COUNT", "AVG", "SUM", "MIN", "MAX"}

    def connect(self) -> sqlite3.Connection:
        """Tra ve ket noi SQLite voi row_factory va foreign keys duoc bat."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def validate_table(self, table: str) -> None:
        """Kiem tra ten bang co trong danh sach cho phep."""
        if table not in self.schema_allowlist:
            raise ValidationError(
                f"Bang '{table}' khong ton tai hoac khong hop le. Cho phep: {list(self.schema_allowlist.keys())}"
            )

    def validate_column(self, table: str, column: str) -> None:
        """Kiem tra ten cot co hop le voi bang da cho."""
        self.validate_table(table)
        if column not in self.schema_allowlist[table]:
            raise ValidationError(
                f"Cot '{column}' khong hop le cho bang '{table}'. Cho phep: {list(self.schema_allowlist[table])}"
            )

    def validate_operator(self, operator: str) -> None:
        """Kiem tra toan tu loc co hop le."""
        if operator.upper() not in self.allowed_operators:
            raise ValidationError(
                f"Toan tu '{operator}' khong duoc ho tro. Cho phep: {list(self.allowed_operators)}"
            )

    def validate_metric(self, metric: str) -> None:
        """Kiem tra ham gom nhom co hop le."""
        if metric.upper() not in self.allowed_metrics:
            raise ValidationError(
                f"Ham thong ke '{metric}' khong duoc ho tro. Cho phep: {list(self.allowed_metrics)}"
            )

    def list_tables(self) -> List[str]:
        """Tra ve danh sach cac bang khong phai he thong."""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row["name"] for row in cursor.fetchall()]
            # Chi lay cac bang co trong allowlist
            return [t for t in tables if t in self.schema_allowlist]
        finally:
            conn.close()

    def get_table_schema(self, table: str) -> List[Dict[str, Any]]:
        """Tra ve schema chi tiet cua mot bang bang PRAGMA table_info."""
        self.validate_table(table)
        conn = self.connect()
        try:
            cursor = conn.cursor()
            # table da duoc validate bang allowlist nen an toan de format truc tiep
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            return [
                {
                    "name": col["name"],
                    "type": col["type"],
                    "notnull": bool(col["notnull"]),
                    "dflt_value": col["dflt_value"],
                    "pk": bool(col["pk"])
                }
                for col in columns
            ]
        finally:
            conn.close()

    def get_full_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Tra ve schema day du cua toan bo database."""
        schema = {}
        for table in self.list_tables():
            schema[table] = self.get_table_schema(table)
        return schema

    def search(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        limit: int = 20,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Tim kiem du lieu tu mot bang.
        Tung phan duoc validate nghiem ngat. Gia tri loc duoc bind vao tham so de chong SQL Injection.
        """
        self.validate_table(table)

        # 1. Validate cot can chon
        if columns:
            for col in columns:
                self.validate_column(table, col)
            select_cols = ", ".join([f'"{c}"' for c in columns])
        else:
            select_cols = "*"

        sql = f'SELECT {select_cols} FROM "{table}"'
        params = []

        # 2. Xay dung WHERE tu filters
        if filters:
            where_clauses = []
            for f in filters:
                if not isinstance(f, dict) or "column" not in f or "operator" not in f or "value" not in f:
                    raise ValidationError("Moi filter phai chua 'column', 'operator' va 'value'")
                
                col = f["column"]
                op = f["operator"].upper()
                val = f["value"]

                self.validate_column(table, col)
                self.validate_operator(op)

                if op == "IN":
                    if not isinstance(val, list):
                        raise ValidationError("Toan tu IN yeu cau gia tri phai la mot danh sach (list)")
                    if not val:
                        raise ValidationError("Toan tu IN khong duoc truyen danh sach rong")
                    placeholders = ", ".join(["?" for _ in val])
                    where_clauses.append(f'"{col}" IN ({placeholders})')
                    params.extend(val)
                else:
                    where_clauses.append(f'"{col}" {op} ?')
                    params.append(val)
            
            sql += " WHERE " + " AND ".join(where_clauses)

        # 3. Sắp xếp ORDER BY
        if order_by:
            self.validate_column(table, order_by)
            direction = "DESC" if descending else "ASC"
            sql += f' ORDER BY "{order_by}" {direction}'

        # 4. Phan trang LIMIT, OFFSET
        if not isinstance(limit, int) or limit < 0:
            raise ValidationError("limit phai la so nguyen khong am")
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("offset phai la so nguyen khong am")
        
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # 5. Thuc thi
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def insert(self, table: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Chen 1 dong moi va tra ve du lieu vua chen.
        """
        self.validate_table(table)
        if not values or not isinstance(values, dict):
            raise ValidationError("Du lieu chen (values) khong duoc de trong va phai la kieu dict")

        # Validate cot duoc chen
        cols = list(values.keys())
        for col in cols:
            self.validate_column(table, col)

        col_str = ", ".join([f'"{c}"' for c in cols])
        placeholders = ", ".join(["?" for _ in cols])
        sql = f'INSERT INTO "{table}" ({col_str}) VALUES ({placeholders})'
        params = list(values.values())

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            last_id = cursor.lastrowid
            conn.commit()

            # Truyp van lai dong vua chen de tra ve
            # Neu co lastrowid va bang la students (id INTEGER AUTOINCREMENT)
            if last_id and table == "students":
                cursor.execute(f'SELECT * FROM "{table}" WHERE id = ?', (last_id,))
                inserted_row = cursor.fetchone()
                return dict(inserted_row) if inserted_row else values
            
            # Truong hop bang co khoa chinh gom (enrollments...) hoac courses
            # Truyp van bang cac gia tri khoa chinh
            if table == "courses":
                cursor.execute('SELECT * FROM "courses" WHERE id = ?', (values.get("id"),))
                inserted_row = cursor.fetchone()
                return dict(inserted_row) if inserted_row else values
            elif table == "enrollments":
                cursor.execute(
                    'SELECT * FROM "enrollments" WHERE student_id = ? AND course_id = ?',
                    (values.get("student_id"), values.get("course_id"))
                )
                inserted_row = cursor.fetchone()
                return dict(inserted_row) if inserted_row else values

            return values
        except sqlite3.IntegrityError as ie:
            raise ValidationError(f"Loi rang buoc du lieu (IntegrityError): {ie}")
        finally:
            conn.close()

    def aggregate(
        self,
        table: str,
        metric: str,
        column: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        group_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Tinh toan thong ke tren bang.
        Vi du: COUNT, AVG, SUM, MIN, MAX
        """
        self.validate_table(table)
        self.validate_metric(metric)

        metric = metric.upper()
        if metric == "COUNT" and (column is None or column == "*"):
            metric_expr = "COUNT(1)"
        else:
            if not column:
                raise ValidationError(f"Ham thong ke '{metric}' yeu cau phai chi dinh cot")
            self.validate_column(table, column)
            metric_expr = f'{metric}("{column}")'

        # Neu co group_by, validate cot group_by
        select_exprs = [f"{metric_expr} AS value"]
        if group_by:
            self.validate_column(table, group_by)
            select_exprs.append(f'"{group_by}"')

        sql = f'SELECT {", ".join(select_exprs)} FROM "{table}"'
        params = []

        # Build WHERE clauses
        if filters:
            where_clauses = []
            for f in filters:
                if not isinstance(f, dict) or "column" not in f or "operator" not in f or "value" not in f:
                    raise ValidationError("Moi filter phai chua 'column', 'operator' va 'value'")
                col = f["column"]
                op = f["operator"].upper()
                val = f["value"]

                self.validate_column(table, col)
                self.validate_operator(op)

                if op == "IN":
                    if not isinstance(val, list):
                        raise ValidationError("Toan tu IN yeu cau danh sach cac gia tri")
                    if not val:
                        raise ValidationError("Toan tu IN khong duoc truyen danh sach rong")
                    placeholders = ", ".join(["?" for _ in val])
                    where_clauses.append(f'"{col}" IN ({placeholders})')
                    params.extend(val)
                else:
                    where_clauses.append(f'"{col}" {op} ?')
                    params.append(val)

            sql += " WHERE " + " AND ".join(where_clauses)

        # Build GROUP BY
        if group_by:
            sql += f' GROUP BY "{group_by}"'

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
