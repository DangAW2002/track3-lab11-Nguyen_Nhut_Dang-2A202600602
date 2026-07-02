import json
from typing import List, Dict, Any, Optional
from fastmcp import FastMCP
from db import SQLiteAdapter, ValidationError

# Khoi tao FastMCP server
mcp = FastMCP("SQLite Lab MCP Server")

# Khoi tao Adapter SQLite
adapter = SQLiteAdapter()


@mcp.tool(name="search")
def search(
    table: str,
    columns: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    limit: int = 20,
    offset: int = 0,
    order_by: Optional[str] = None,
    descending: bool = False
) -> str:
    """
    Tim kiem va truy van du lieu tu mot bang trong database.
    
    Args:
        table: Ten bang can truy van ('students', 'courses', 'enrollments').
        columns: Danh sach cac cot muon lay (mac dinh la tat ca cac cot).
        filters: Danh sach cac bo loc. Moi bo loc la mot dict dang:
                 {"column": "ten_cot", "operator": "=", "value": "gia_tri"}
                 Cac toan tu ho tro: =, !=, >, <, >=, <=, LIKE, IN.
                 Luu y: Voi toan tu 'IN', 'value' phai la mot list cac gia tri.
        limit: So dong toi da muon lay (mac dinh: 20).
        offset: So dong muon bo qua (phan trang, mac dinh: 0).
        order_by: Ten cot de sap xep ket qua.
        descending: True de sap xep giam dan (DESC), False de sap xep tang dan (ASC).
    """
    try:
        results = adapter.search(
            table=table,
            columns=columns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending
        )
        return json.dumps(results, indent=2, ensure_ascii=False)
    except ValidationError as ve:
        raise ValueError(f"Loi xac thuc yeu cau: {ve}")
    except Exception as e:
        raise RuntimeError(f"Loi he thong khi tim kiem: {e}")


@mcp.tool(name="insert")
def insert(table: str, values: Dict[str, Any]) -> str:
    """
    Chen mot dong du lieu moi vao bang trong database.
    
    Args:
        table: Ten bang muon chen ('students', 'courses', 'enrollments').
        values: Dict anh xa giua ten cot va gia tri can chen. Vi du:
                students -> {"name": "Gia Huy", "cohort": "A1", "age": 21}
                courses -> {"id": "CS301", "name": "Computer Networks", "credits": 3}
                enrollments -> {"student_id": 1, "course_id": "CS101", "score": 92.5}
    """
    try:
        inserted_payload = adapter.insert(table=table, values=values)
        return json.dumps(
            {
                "status": "success",
                "message": f"Da chen thanh cong vao bang '{table}'",
                "data": inserted_payload
            },
            indent=2,
            ensure_ascii=False
        )
    except ValidationError as ve:
        raise ValueError(f"Loi xac thuc du lieu chen: {ve}")
    except Exception as e:
        raise RuntimeError(f"Loi he thong khi chen du lieu: {e}")


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    group_by: Optional[str] = None
) -> str:
    """
    Thuc hien tinh toan thong ke/gom nhom tren mot bang (COUNT, AVG, SUM, MIN, MAX).
    
    Args:
        table: Ten bang can thong ke ('students', 'courses', 'enrollments').
        metric: Ham thong ke muon dung ('COUNT', 'AVG', 'SUM', 'MIN', 'MAX').
        column: Ten cot muon ap dung ham thong ke (voi COUNT, cot co the la None hoac '*').
        filters: Bo loc ap dung truoc khi thong ke. Dang list cac dict loc giong nhu o tool search.
        group_by: Cot muon dung de gom nhom ket qua (GROUP BY).
    """
    try:
        results = adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by
        )
        return json.dumps(results, indent=2, ensure_ascii=False)
    except ValidationError as ve:
        raise ValueError(f"Loi xac thuc aggregate: {ve}")
    except Exception as e:
        raise RuntimeError(f"Loi he thong khi thong ke: {e}")


@mcp.resource("schema://database")
def database_schema() -> str:
    """
    Xem toan bo schema cua tat ca cac bang trong co so du lieu SQLite.
    """
    try:
        schema = adapter.get_full_schema()
        return json.dumps(schema, indent=2, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"Loi khi doc schema database: {e}")


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """
    Xem schema chi tiet cua mot bang cu the trong co so du lieu.
    
    Args:
        table_name: Ten bang can xem schema ('students', 'courses', 'enrollments').
    """
    try:
        # validate truoc de bao loi som truoc khi goi tiep
        adapter.validate_table(table_name)
        schema = adapter.get_table_schema(table_name)
        return json.dumps({table_name: schema}, indent=2, ensure_ascii=False)
    except ValidationError as ve:
        raise ValueError(f"Ten bang khong hop le: {ve}")
    except Exception as e:
        raise RuntimeError(f"Loi khi doc schema bang: {e}")


if __name__ == "__main__":
    # Khoi chay server (mac dinh dung stdio transport)
    mcp.run()
