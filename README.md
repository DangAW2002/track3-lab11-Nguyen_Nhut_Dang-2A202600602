# SQLite Database MCP Server (Lab 11)

Dự án này là một Model Context Protocol (MCP) server được xây dựng bằng **FastMCP** (Python) và **SQLite**, cho phép các AI Client (như Gemini CLI, Claude Code) truy vấn, chèn dữ liệu và thống kê từ cơ sở dữ liệu học tập một cách an toàn (chống SQL Injection thông qua cơ chế kiểm tra allowlist nghiêm ngặt và bind tham số).

---

## 📂 Cấu trúc thư mục (Project Structure)

```text
track3-lab11-Nguyen_Nhut_Dang-2A202600602/
├── .gemini/
│   └── settings.json       # Cấu hình MCP server cho Gemini CLI
├── .mcp.json               # Cấu hình MCP server cho Claude Code
├── implementation/
│   ├── db.py               # Adapter SQLite (Logic truy vấn & Bảo mật)
│   ├── init_db.py          # Script khởi tạo database & seed dữ liệu mẫu
│   ├── mcp_server.py       # Điểm khởi chạy FastMCP Server (Tools & Resources)
│   ├── verify_server.py    # Kịch bản kiểm thử tích hợp (Smoke test)
│   └── tests/
│       └── test_server.py  # Bộ unit tests tự động (pytest)
├── README.md               # Hướng dẫn chi tiết này
├── Rubric.md               # Tiêu chí đánh giá bài Lab
└── Tips.md                 # Mẹo tích hợp các Client
```

---

## 🛠️ Hướng dẫn thiết lập (Setup Instructions)

### 1. Kích hoạt môi trường Conda
Sử dụng môi trường conda `ai-20k-3.11` như được yêu cầu:
```bash
conda activate ai-20k-3.11
```

### 2. Cài đặt các thư viện cần thiết
Cài đặt `fastmcp` bằng `pip`:
```bash
C:\Users\Dang\miniforge3\envs\ai-20k-3.11\python.exe -m pip install fastmcp
```

### 3. Khởi tạo Cơ sở dữ liệu (SQLite)
Chạy script `init_db.py` để tạo file DB `implementation/sqlite_lab.db` và seed dữ liệu mẫu:
```bash
C:\Users\Dang\miniforge3\envs\ai-20k-3.11\python.exe implementation/init_db.py
```
*Dữ liệu mẫu chứa các bảng: `students`, `courses`, và `enrollments`.*

---

## ⚙️ Mô tả các tính năng MCP (FastMCP Specifications)

### 1. MCP Tools (Công cụ cung cấp cho AI)
*   **`search`**: Tìm kiếm dòng trong bảng với các tùy chọn: chọn cột (`columns`), bộ lọc (`filters`), giới hạn (`limit`), bỏ qua (`offset`), và sắp xếp (`order_by`, `descending`).
    *   *Toán tử lọc hỗ trợ:* `=`, `!=`, `>`, `<`, `>=`, `<=`, `LIKE`, `IN`.
*   **`insert`**: Chèn dòng dữ liệu mới vào bảng (kiểm tra chặt chẽ khóa ngoại và dữ liệu rỗng).
*   **`aggregate`**: Tính toán các chỉ số thống kê (`COUNT`, `AVG`, `SUM`, `MIN`, `MAX`) kèm theo tùy chọn lọc và gom nhóm (`group_by`).

### 2. MCP Resources (Tài nguyên tĩnh/động)
*   **`schema://database`**: Cung cấp cấu trúc schema JSON của toàn bộ cơ sở dữ liệu.
*   **`schema://table/{table_name}`**: Cung cấp cấu trúc schema chi tiết cho một bảng cụ thể (ví dụ: `schema://table/students`).

---

## 🛡️ Cơ chế bảo mật và an toàn đầu vào

Hệ thống ngăn chặn **SQL Injection** và các lỗi logic thông qua:
1.  **Allowlist kiểm tra định danh**: Chỉ cho phép thao tác trên các bảng và cột được khai báo trước. Bất kỳ tên bảng hoặc cột lạ nào đều bị từ chối ngay lập tức bằng `ValidationError`.
2.  **Allowlist toan tử và hàm**: Giới hạn nghiêm ngặt các toán tử so sánh và các hàm aggregate.
3.  **Tham số hóa câu lệnh (Parameterized Queries)**: Sử dụng ký tự placeholder `?` cho mọi giá trị đầu vào từ người dùng khi thực hiện truy vấn hoặc chèn dòng dữ liệu mới.

---

## 🧪 Quy trình kiểm thử và xác minh (Testing & Verification)

### 1. Chạy kịch bản kiểm thử Adapter
Chạy kiểm tra trực tiếp adapter SQLite để verify toàn bộ chức năng (bao gồm cả các test case bảo mật):
```bash
C:\Users\Dang\miniforge3\envs\ai-20k-3.11\python.exe implementation/verify_server.py
```

### 2. Chạy bộ Unit Tests với Pytest
Chạy bộ kiểm thử tự động (sử dụng cờ `--disable-plugin-autoload` để tránh các lỗi xung đột SSL từ các plugin bên thứ ba như `deepeval` trên Windows):
```bash
C:\Users\Dang\miniforge3\envs\ai-20k-3.11\python.exe -m pytest --disable-plugin-autoload implementation/tests/
```
*Kết quả mong đợi: Toàn bộ các test case vượt qua thành công (7 passed).*

### 3. Kiểm tra bằng FastMCP CLI
Kiểm tra khả năng tự phát hiện (discoverability) các công cụ và tài nguyên của server:
```bash
C:\Users\Dang\miniforge3\envs\ai-20k-3.11\Scripts\fastmcp.exe inspect --skip-env implementation/mcp_server.py
```

### 4. Kiểm tra bằng MCP Inspector
Bật giao diện trực quan MCP Inspector để gọi thử trực tiếp các công cụ:
```bash
npx @modelcontextprotocol/inspector C:\Users\Dang\miniforge3\envs\ai-20k-3.11\python.exe implementation/mcp_server.py
```

---

## 💻 Cấu hình Client (Client Configuration)

### 1. Gemini CLI
Cấu hình đã được ghi đè tại dự án ở địa chỉ `.gemini/settings.json`. Để đăng ký thủ công ở cấp hệ thống:
```bash
gemini mcp add sqlite-lab C:\Users\Dang\miniforge3\envs\ai-20k-3.11\python.exe C:\Users\Dang\Desktop\ai-20k\BT_LAB\track3-lab11-Nguyen_Nhut_Dang-2A202600602\implementation\mcp_server.py --description "SQLite lab FastMCP server" --timeout 10000
```
Sau đó bạn có thể đặt câu hỏi:
```bash
gemini --allowed-mcp-server-names sqlite-lab --yolo -p "Show me the list of students in A1"
```

### 2. Claude Code
Cấu hình đã được định nghĩa sẵn trong `.mcp.json` tại thư mục gốc của bài Lab. Claude Code sẽ tự động tải cấu hình khi bạn khởi động nó trong thư mục này.
Bạn có thể tham chiếu schema trực tiếp:
```text
Show me the students schema by querying @sqlite-lab:schema://table/students
```