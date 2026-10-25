from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


class Msg(BaseModel):
    message: str


# ---------- auth ----------
class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z][A-Za-z0-9_]{2,29}$")
    password: str = Field(min_length=8, max_length=72)
    email: EmailStr | None = None
    nickname: str = Field(default="", max_length=50)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshIn(BaseModel):
    refresh_token: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=72)


class ProfileIn(BaseModel):
    nickname: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)


# ---------- rbac ----------
class PermissionOut(ORM):
    id: int
    code: str
    name: str
    group: str
    description: str


class RoleBrief(ORM):
    id: int
    code: str
    name: str


class RoleOut(ORM):
    id: int
    code: str
    name: str
    description: str
    is_system: bool
    is_active: bool
    sort: int
    created_at: datetime
    permissions: list[str] = []
    user_count: int = 0


class RoleIn(BaseModel):
    code: str = Field(min_length=2, max_length=50, pattern=r"^[a-z][a-z0-9_]{1,49}$")
    name: str = Field(min_length=1, max_length=50)
    description: str = Field(default="", max_length=255)
    is_active: bool = True
    sort: int = 0
    permissions: list[str] = []


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    sort: int | None = None
    permissions: list[str] | None = None


class UserOut(ORM):
    id: int
    username: str
    email: str | None
    nickname: str
    phone: str | None
    avatar: str | None
    is_active: bool
    is_superuser: bool
    must_change_password: bool
    last_login_at: datetime | None
    last_login_ip: str | None
    remark: str
    created_at: datetime
    roles: list[RoleBrief]


class MeOut(UserOut):
    permissions: list[str]


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z][A-Za-z0-9_]{2,29}$")
    password: str = Field(min_length=8, max_length=72)
    email: EmailStr | None = None
    nickname: str = Field(default="", max_length=50)
    phone: str | None = Field(default=None, max_length=30)
    is_active: bool = True
    role_ids: list[int] = []
    remark: str = Field(default="", max_length=255)
    must_change_password: bool = True


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    nickname: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None
    role_ids: list[int] | None = None
    remark: str | None = Field(default=None, max_length=255)


class ResetPasswordIn(BaseModel):
    new_password: str = Field(min_length=8, max_length=72)


# ---------- content ----------
class ChapterBrief(ORM):
    id: int
    title: str
    word_count: int
    sort: int


class ChapterOut(ChapterBrief):
    document_id: int
    content: str
    updated_at: datetime


class DocumentOut(ORM):
    id: int
    slug: str
    title: str
    category: str
    summary: str
    word_count: int
    sort: int
    is_published: bool
    view_count: int
    updated_at: datetime
    chapter_count: int = 0


class DocumentDetail(DocumentOut):
    chapters: list[ChapterBrief]


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    summary: str | None = None
    sort: int | None = None
    is_published: bool | None = None


class DocumentCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=50)
    summary: str = ""
    sort: int = 0
    is_published: bool = False


class ChapterIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = ""
    sort: int | None = None


class CaseOut(ORM):
    id: int
    seq: int
    date_text: str
    year: int | None
    patient: str
    diagnosis: str
    pathogenesis: str
    western_view: str
    prescription: str
    acupuncture: str
    principle: str
    outcome: str
    advice: str
    comment: str
    is_published: bool


class CaseIn(BaseModel):
    seq: int | None = None
    date_text: str = ""
    year: int | None = None
    patient: str = ""
    diagnosis: str = Field(min_length=1)
    pathogenesis: str = ""
    western_view: str = ""
    prescription: str = ""
    acupuncture: str = ""
    principle: str = ""
    outcome: str = ""
    advice: str = ""
    comment: str = ""
    is_published: bool = True


class SearchHit(BaseModel):
    type: str  # chapter | case
    id: int
    title: str
    subtitle: str
    snippet: str
    document_slug: str | None = None
    chapter_id: int | None = None


class FavoriteIn(BaseModel):
    target_type: str = Field(pattern=r"^(document|case)$")
    target_id: int


class FavoriteOut(BaseModel):
    id: int
    target_type: str
    target_id: int
    title: str
    subtitle: str
    created_at: datetime


class AuditOut(ORM):
    id: int
    user_id: int | None
    username: str
    action: str
    target: str
    detail: str
    ip: str
    success: bool
    created_at: datetime


class ChatMessage(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str = Field(min_length=1, max_length=8000)


class ChatIn(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
