# 倪海厦 · 经方中医知识平台

基于开源知识库 [jangviktor-web/nihaixia](https://github.com/jangviktor-web/nihaixia) 重构的前后端分离 Web 应用：
伤寒金匮、黄帝内经、针灸本草讲义在线研读，1256 例结构化医案检索，全文搜索，AI 经方问诊，以及完整的用户与角色权限管理。

## 功能

| 模块 | 说明 |
| --- | --- |
| 典籍书阁 | 36 卷讲义按 7 大门类展示，自动分章（339 章），阅读器带章节目录、本章纲目、字号调节、收藏、上下章 |
| 医案库 | 1256 例倪师医案结构化数据，可按全部字段 / 诊断 / 方剂 / 病机 / 针灸 / 倪师观点检索，按年份筛选 |
| 全文检索 | 一个关键词同时检索讲义与医案，结果高亮，点击直达原文并定位关键词 |
| 经方问诊 | 以原项目 `SKILL.md` 为系统提示，自动检索知识库相关章节作为参考，流式输出并标注参考原文；每人每日限额 |
| 个人中心 | 资料修改、修改密码、退出所有设备、我的收藏 |
| 管理后台 | 控制台（统计、趋势图、角色分布、最近操作）、用户管理、角色权限、典籍管理（Markdown 分栏编辑）、医案管理、操作日志 |

### 权限模型（RBAC）

用户 ←多对多→ 角色 ←多对多→ 权限点。权限点定义在 `backend/app/permissions.py`，启动时自动同步到数据库。

| 内置角色 | 权限 |
| --- | --- |
| 超级管理员 `super_admin` | 全部权限，不可删除、不可改权限 |
| 管理员 `admin` | 用户增改、重置密码、查看角色、内容管理、日志（不能改角色授权、不能删用户） |
| 内容编辑 `editor` | 典籍与医案维护 |
| 注册会员 `member` | 查阅医案、AI 问诊（新注册用户默认角色） |

可在后台新建任意角色并勾选权限，修改即时生效。安全措施：

- 管理者只能管理权限不超过自己的用户，只能分配自己拥有的权限对应的角色；超级管理员只能由超级管理员管理
- 不能删除/禁用自己，至少保留一个超级管理员
- JWT 访问令牌（30 分钟）+ 刷新令牌（7 天）；改密码、禁用、强制下线、改角色会立即使旧令牌失效
- 连续 5 次密码错误锁定 15 分钟；密码 bcrypt 加密，要求 8 位以上且含字母和数字
- 管理员创建或重置的账号首次登录必须修改密码
- 所有登录与管理操作写入操作日志（含 IP）

## 技术栈

- 后端：Python 3.13 · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 16（开发可用 SQLite）· PyJWT · bcrypt · Anthropic SDK
- 前端：Vue 3 · TypeScript · Vite · Pinia · Vue Router · Element Plus · ECharts · markdown-it + DOMPurify
- 部署：Docker Compose（Nginx 静态托管 + 反向代理、Gunicorn/Uvicorn、PostgreSQL）

```
nihaixia-app/
├── backend/
│   ├── app/
│   │   ├── main.py            # 应用入口
│   │   ├── models.py          # 数据模型
│   │   ├── permissions.py     # 权限点与内置角色
│   │   ├── routers/           # auth / users / roles / documents / cases / misc / ai
│   │   └── services/          # 内容导入、初始化、AI 问诊、审计
│   ├── alembic/               # 数据库迁移
│   ├── content/               # 原仓库 Markdown 知识库（首次启动自动导入）
│   └── tests/                 # 接口测试
├── frontend/
│   ├── src/views/             # 前台页面 + admin 后台页面
│   ├── src/styles/main.scss   # 中医风格设计系统（宣纸 / 浓墨 / 朱砂 / 青黛）
│   └── nginx/default.conf
└── docker-compose.yml
```

## 上线部署（Docker Compose）

```bash
cp .env.example .env
# 编辑 .env：至少设置 DB_PASSWORD 和 SECRET_KEY，建议设置 ADMIN_PASSWORD
python3 -c "import secrets;print(secrets.token_urlsafe(48))"   # 生成 SECRET_KEY

docker compose up -d --build
```

访问 `http://服务器IP`（端口由 `HTTP_PORT` 控制）。首次启动会自动：执行数据库迁移 → 同步权限与内置角色 → 创建超级管理员 → 导入全部典籍与医案。

- 若未设置 `ADMIN_PASSWORD`，随机密码会打印在日志里：`docker compose logs backend | grep 初始管理员`
- 生产环境建议在前面再加一层 HTTPS（如 Caddy / 云负载均衡 / 宿主机 Nginx + Let's Encrypt）
- 数据保存在 `pgdata` 卷中，备份：`docker compose exec db pg_dump -U nihaixia nihaixia > backup.sql`
- 开启 AI 问诊：在 `.env` 设置 `ANTHROPIC_API_KEY`，可用 `AI_MODEL`、`AI_DAILY_LIMIT` 调整模型和每日次数

常用运维命令：

```bash
docker compose exec backend python -m app.cli import --replace        # 用 content/ 重新导入全部内容（覆盖后台修改）
docker compose exec backend python -m app.cli create-admin 用户名 密码   # 新增超级管理员
```

## 本地开发

```bash
# 后端（默认使用 SQLite：backend/data.db）
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
ADMIN_PASSWORD=Admin12345 uvicorn app.main:app --reload     # http://127.0.0.1:8000/api/docs
pytest                                                       # 运行测试

# 前端
cd frontend
npm install
npm run dev                                                  # http://localhost:5173 ，/api 自动代理到 8000
```

## 主要配置项

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | SQLite | 例：`postgresql+psycopg://user:pass@host:5432/db` |
| `SECRET_KEY` | — | JWT 签名密钥，生产必填，≥32 位 |
| `ENVIRONMENT` | development | `production` 时关闭 API 文档并强制检查密钥 |
| `ALLOW_REGISTRATION` | true | 是否开放前台注册 |
| `ACCESS_TOKEN_MINUTES` / `REFRESH_TOKEN_DAYS` | 30 / 7 | 令牌有效期 |
| `MAX_FAILED_LOGINS` / `LOCKOUT_MINUTES` | 5 / 15 | 登录锁定策略 |
| `ANTHROPIC_API_KEY` | 空 | 为空则不开放 AI 问诊 |
| `AI_MODEL` | claude-opus-5-5 | 问诊所用模型 |
| `AI_DAILY_LIMIT` | 30 | 每人每日问诊次数（超级管理员不限） |

## 版权与声明

- 知识库内容来自 [jangviktor-web/nihaixia](https://github.com/jangviktor-web/nihaixia)，遵循木兰宽松许可证 MulanPSL-2.0。
- 本平台内容仅供中医学习交流，不构成任何诊疗建议；AI 问诊结果仅供参考，用药请遵执业中医师指导。
