# MySQL 数据库初始化

## 1. 创建数据库

先使用你本机 MySQL 管理员账号创建数据库（数据库名可以保持默认）：

```sql
CREATE DATABASE knowledge_base
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

如果准备使用独立账号：

```sql
CREATE USER 'knowledge'@'localhost' IDENTIFIED BY 'change-me';
GRANT ALL PRIVILEGES ON knowledge_base.* TO 'knowledge'@'localhost';
FLUSH PRIVILEGES;
```

## 2. 配置连接地址

在项目根目录 `.env` 中加入实际连接信息：

```dotenv
MYSQL_URL=mysql+asyncmy://用户名:密码@127.0.0.1:3306/knowledge_base?charset=utf8mb4
SQL_ECHO=0
```

密码包含 `@`、`#`、`/` 等特殊字符时需要进行 URL 编码。

## 3. 执行迁移

在项目根目录运行：

```powershell
uv run alembic upgrade head
```

迁移会创建用户、角色、权限、知识库、文档、文档分段、标签和操作日志表。

查看当前版本：

```powershell
uv run alembic current
```

## 4. 初始化基础数据

```powershell
uv run python -m backend.scripts.init_data
```

默认创建：

- `admin` 管理员账号
- `admin` 和 `user` 角色
- 基础权限
- 工业设备手册、网络设备资料、售后服务知识三个知识库

生产环境请设置 `DEFAULT_ADMIN_PASSWORD` 后再执行初始化脚本，避免使用默认密码。

## 5. 检查连接

启动 FastAPI 后访问：

```text
GET /health/db
```

成功响应：

```json
{"code": 0, "message": "ok", "data": {"status": "ok", "database": "mysql"}}
```

## 目录说明

- `backend/app/db/session.py`：异步 engine、Session 和 Base
- `backend/app/db/models.py`：SQLAlchemy 业务模型
- `backend/alembic/versions/20260831_0001_initial.py`：初始迁移
- `backend/scripts/init_data.py`：角色、管理员和知识库种子数据