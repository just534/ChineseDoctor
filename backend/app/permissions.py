"""权限点目录：代码即真相，启动时同步到数据库。"""

PERMISSIONS: list[tuple[str, str, str]] = [
    # (code, name, group)
    ("dashboard:view", "查看控制台", "系统"),
    ("user:read", "查看用户", "用户管理"),
    ("user:create", "新增用户", "用户管理"),
    ("user:update", "编辑用户", "用户管理"),
    ("user:delete", "删除用户", "用户管理"),
    ("user:reset_password", "重置密码", "用户管理"),
    ("role:read", "查看角色", "角色权限"),
    ("role:manage", "管理角色与授权", "角色权限"),
    ("document:manage", "管理典籍", "内容管理"),
    ("case:read", "查阅医案库", "内容管理"),
    ("case:manage", "管理医案", "内容管理"),
    ("ai:chat", "AI 问诊", "智能服务"),
    ("audit:read", "查看操作日志", "系统"),
]

PERMISSION_CODES = {c for c, _, _ in PERMISSIONS}

# 内置角色 -> 权限点（super_admin 走 is_superuser 全通）
BUILTIN_ROLES: list[dict] = [
    {
        "code": "super_admin",
        "name": "超级管理员",
        "description": "拥有全部权限，不可删除",
        "permissions": sorted(PERMISSION_CODES),
        "sort": 0,
    },
    {
        "code": "admin",
        "name": "管理员",
        "description": "管理用户与内容，不可修改角色授权",
        "permissions": [
            "dashboard:view",
            "user:read",
            "user:create",
            "user:update",
            "user:reset_password",
            "role:read",
            "document:manage",
            "case:read",
            "case:manage",
            "ai:chat",
            "audit:read",
        ],
        "sort": 10,
    },
    {
        "code": "editor",
        "name": "内容编辑",
        "description": "维护典籍与医案",
        "permissions": ["dashboard:view", "document:manage", "case:read", "case:manage", "ai:chat"],
        "sort": 20,
    },
    {
        "code": "member",
        "name": "注册会员",
        "description": "注册用户默认角色：查阅医案、AI 问诊",
        "permissions": ["case:read", "ai:chat"],
        "sort": 30,
    },
]
