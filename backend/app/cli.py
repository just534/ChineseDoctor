"""命令行工具

python -m app.cli init                      # 同步权限/角色、创建管理员、导入内容（幂等）
python -m app.cli import --replace          # 重新导入全部 Markdown 内容（覆盖数据库中的修改）
python -m app.cli create-admin NAME PASS    # 新建超级管理员
"""

import argparse
import sys

from sqlalchemy import select

from .config import get_settings
from .db import SessionLocal
from .models import Role, User
from .security import hash_password, validate_password_strength
from .services.bootstrap import bootstrap
from .services.importer import import_all


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    p_imp = sub.add_parser("import")
    p_imp.add_argument("--replace", action="store_true")
    p_adm = sub.add_parser("create-admin")
    p_adm.add_argument("username")
    p_adm.add_argument("password")
    args = parser.parse_args()
    settings = get_settings()

    with SessionLocal() as db:
        if args.cmd == "init":
            bootstrap(db)
            import_all(db, settings.content_dir)
        elif args.cmd == "import":
            print("导入：%d 篇典籍，%d 例医案" % import_all(db, settings.content_dir, replace=args.replace))
        elif args.cmd == "create-admin":
            if err := validate_password_strength(args.password):
                sys.exit(err)
            if db.scalar(select(User).where(User.username == args.username)):
                sys.exit("用户已存在")
            u = User(username=args.username, nickname=args.username, password_hash=hash_password(args.password),
                     is_superuser=True)
            u.roles = [db.scalar(select(Role).where(Role.code == "super_admin"))]
            db.add(u)
            db.commit()
            print("已创建超级管理员", args.username)


if __name__ == "__main__":
    main()
