"""MySQL-backed administration API.

Permission definitions are owned by the code registry.  API consumers can only view
registered permissions, toggle their state, and assign them to roles.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.api.schemas import (
    ChunkOut, DocumentCreate, DocumentDetailOut, DocumentListOut, DocumentTagsUpdate,
    DocumentUpdate, DocumentUploadOut, LibraryCreate, LibraryOut, LibraryUpdate,
    MemberCreate, MemberOut, OperationLogOut, OperationLogPageOut, PermissionOut, PermissionUpdate,
    RoleCreate, RoleOut, RoleUpdate, TagCreate, TagOut, TagUpdate, UserCreate,
    UserOut, UserUpdate,
)
from backend.app.core.audit import log_operation
from backend.app.core.auth import hash_password, require_management_access
from backend.app.core.permissions import REGISTERED_PERMISSION_CODES, is_registered_permission
from backend.app.db.models import (
    Document, DocumentChunk, DocumentTag, Library, LibraryMember, OperationLog,
    Permission, Role, Tag, User,
)
from backend.app.db.session import get_db

router = APIRouter(prefix="/api/v1", tags=["mysql"], dependencies=[Depends(require_management_access)])


async def get_or_404(session: AsyncSession, model: type, item_id: int, label: str):
    item = await session.get(model, item_id)
    if item is None:
        raise HTTPException(404, f"{label}不存在")
    return item


async def commit(session: AsyncSession, duplicate_message: str) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(400, duplicate_message) from exc


log = log_operation


def user_out(user: User) -> dict:
    return {
        "id": user.id, "username": user.username, "email": user.email, "phone": user.phone,
        "display_name": user.display_name, "avatar_url": user.avatar_url, "status": user.status,
        "last_login_at": user.last_login_at,
        "roles": [role.code for role in user.roles if role.deleted_at is None],
    }


def role_out(role: Role) -> dict:
    return {
        "id": role.id, "code": role.code, "name": role.name, "description": role.description,
        "status": role.status, "deleted_at": role.deleted_at, "deleted_by": role.deleted_by,
        "permissions": [
            permission.code for permission in role.permissions
            if permission.deleted_at is None and is_registered_permission(permission.code)
        ],
    }


def permission_out(permission: Permission) -> dict:
    return {
        "id": permission.id, "code": permission.code, "name": permission.name,
        "description": permission.description, "status": permission.status,
        "deleted_at": permission.deleted_at, "deleted_by": permission.deleted_by,
        "parent_id": permission.parent_id,
    }


def document_out(document: Document, *, chunk_count: int = 0, tags: list[str] | None = None, library_name: str | None = None) -> dict:
    return {
        "id": document.id, "library_id": document.library_id, "title": document.title,
        "original_filename": document.original_filename, "storage_key": document.storage_key,
        "mime_type": document.mime_type, "file_size": document.file_size,
        "file_hash": document.file_hash, "version": document.version, "status": document.status,
        "parse_error": document.parse_error, "uploaded_by": document.uploaded_by,
        "published_at": document.published_at, "created_at": document.created_at,
        "updated_at": document.updated_at, "chunk_count": chunk_count, "tags": tags or [],
        "library_name": library_name,
    }


async def resolve_registered_permissions(session: AsyncSession, codes: list[str]) -> list[Permission]:
    requested = list(dict.fromkeys(codes))
    if set(requested) - REGISTERED_PERMISSION_CODES:
        raise HTTPException(400, "只能分配权限注册表中的权限")
    if not requested:
        return []
    result = await session.execute(
        select(Permission).where(Permission.code.in_(requested), Permission.deleted_at.is_(None))
    )
    permissions = list(result.scalars())
    if len(permissions) != len(requested):
        raise HTTPException(400, "部分权限不存在、已删除或尚未完成同步")
    return permissions


async def registered_permission_or_404(session: AsyncSession, permission_id: int) -> Permission:
    permission = await get_or_404(session, Permission, permission_id, "权限")
    if not is_registered_permission(permission.code):
        raise HTTPException(404, "权限不存在")
    return permission


@router.get("/users", response_model=list[UserOut])
async def list_users(include_deleted: bool = Query(False), session: AsyncSession = Depends(get_db)):
    statement = select(User).options(selectinload(User.roles)).order_by(User.id.desc())
    if not include_deleted:
        statement = statement.where(User.deleted_at.is_(None))
    return [user_out(item) for item in (await session.execute(statement)).scalars().unique()]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(Role).where(Role.code.in_(list(dict.fromkeys(payload.role_codes))), Role.deleted_at.is_(None))
    )
    roles = list(result.scalars())
    if len(roles) != len(set(payload.role_codes)):
        raise HTTPException(400, "存在不可用的角色")
    user = User(
        username=payload.username, display_name=payload.display_name, email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(f"{payload.username[:3]}{payload.phone}"),
        roles=roles,
    )
    session.add(user)
    await session.flush()
    await log(session, "create", "user", user.id)
    await commit(session, "用户名、邮箱或手机号已存在")
    return user_out(user)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: int, payload: UserUpdate, session: AsyncSession = Depends(get_db)):
    # Preload the collection before replacing this async many-to-many relationship.
    result = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "用户不存在")
    for field, value in payload.model_dump(exclude_unset=True, exclude={"role_codes", "password"}).items():
        setattr(user, field, value)
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.role_codes is not None:
        result = await session.execute(
            select(Role).where(Role.code.in_(list(dict.fromkeys(payload.role_codes))), Role.deleted_at.is_(None))
        )
        roles = list(result.scalars())
        if len(roles) != len(set(payload.role_codes)):
            raise HTTPException(400, "存在不可用的角色")
        user.roles = roles
    await log(session, "update", "user", user.id)
    await commit(session, "用户名、邮箱或手机号已存在")
    await session.refresh(user, attribute_names=["roles"])
    return user_out(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await get_or_404(session, User, user_id, "用户")
    user.deleted_at = datetime.now()
    await log(session, "delete", "user", user.id)
    await commit(session, "删除用户失败")


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(include_deleted: bool = Query(False), session: AsyncSession = Depends(get_db)):
    statement = select(Role).options(selectinload(Role.permissions)).order_by(Role.id.desc())
    if not include_deleted:
        statement = statement.where(Role.deleted_at.is_(None))
    return [role_out(item) for item in (await session.execute(statement)).scalars().unique()]


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(payload: RoleCreate, session: AsyncSession = Depends(get_db)):
    role = Role(
        code=payload.code, name=payload.name, description=payload.description,
        permissions=await resolve_registered_permissions(session, payload.permission_codes),
    )
    session.add(role)
    await session.flush()
    await log(session, "create", "role", role.id)
    await commit(session, "角色编码已存在")
    return role_out(role)


@router.patch("/roles/{role_id}", response_model=RoleOut)
async def update_role(role_id: int, payload: RoleUpdate, session: AsyncSession = Depends(get_db)):
    # Preload the collection before replacing this async many-to-many relationship.
    result = await session.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(404, "角色不存在")
    for field, value in payload.model_dump(exclude_unset=True, exclude={"permission_codes"}).items():
        setattr(role, field, value)
    if payload.permission_codes is not None:
        role.permissions = await resolve_registered_permissions(session, payload.permission_codes)
    await log(session, "update", "role", role.id)
    await commit(session, "更新角色失败")
    await session.refresh(role, attribute_names=["permissions"])
    return role_out(role)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(role_id: int, session: AsyncSession = Depends(get_db)):
    role = await get_or_404(session, Role, role_id, "角色")
    role.deleted_at = datetime.now()
    await log(session, "delete", "role", role.id)
    await commit(session, "删除角色失败")


@router.post("/roles/{role_id}/restore", response_model=RoleOut)
async def restore_role(role_id: int, session: AsyncSession = Depends(get_db)):
    # Preload the collection before replacing this async many-to-many relationship.
    result = await session.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(404, "角色不存在")
    role.deleted_at = None
    role.deleted_by = None
    await log(session, "restore", "role", role.id)
    await commit(session, "恢复角色失败")
    await session.refresh(role, attribute_names=["permissions"])
    return role_out(role)


@router.get("/permissions", response_model=list[PermissionOut])
async def list_permissions(session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(Permission)
        .where(Permission.code.in_(REGISTERED_PERMISSION_CODES))
        .order_by(Permission.parent_id.is_not(None), Permission.id)
    )
    return [permission_out(item) for item in result.scalars()]


@router.post("/permissions", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
async def create_permission():
    raise HTTPException(405, "权限由系统注册表维护，不能手动新增")


@router.patch("/permissions/{permission_id}", response_model=PermissionOut)
async def update_permission(permission_id: int, payload: PermissionUpdate, session: AsyncSession = Depends(get_db)):
    permission = await registered_permission_or_404(session, permission_id)
    if payload.status is not None:
        permission.status = payload.status
    await log(session, "update", "permission", permission.id)
    await commit(session, "更新权限失败")
    return permission_out(permission)


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
async def delete_permission(permission_id: int, session: AsyncSession = Depends(get_db)):
    await registered_permission_or_404(session, permission_id)
    raise HTTPException(405, "注册权限不能删除，可通过启用或停用控制状态")


@router.post("/permissions/{permission_id}/restore", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
async def restore_permission(permission_id: int, session: AsyncSession = Depends(get_db)):
    await registered_permission_or_404(session, permission_id)
    raise HTTPException(405, "注册权限由系统自动同步，无需手动恢复")


@router.get("/libraries", response_model=list[LibraryOut])
async def list_libraries(include_deleted: bool = Query(False), session: AsyncSession = Depends(get_db)):
    statement = select(Library).order_by(Library.id.desc())
    if not include_deleted:
        statement = statement.where(Library.deleted_at.is_(None))
    return list((await session.execute(statement)).scalars())


@router.post("/libraries", response_model=LibraryOut, status_code=status.HTTP_201_CREATED)
async def create_library(payload: LibraryCreate, session: AsyncSession = Depends(get_db)):
    library = Library(**payload.model_dump())
    session.add(library)
    await session.flush()
    await log(session, "create", "library", library.id)
    await commit(session, "知识库编码已存在")
    return library


@router.patch("/libraries/{library_id}", response_model=LibraryOut)
async def update_library(library_id: int, payload: LibraryUpdate, session: AsyncSession = Depends(get_db)):
    library = await get_or_404(session, Library, library_id, "知识库")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(library, field, value)
    await log(session, "update", "library", library.id)
    await commit(session, "更新知识库失败")
    await session.refresh(library)
    return library


@router.delete("/libraries/{library_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_library(library_id: int, session: AsyncSession = Depends(get_db)):
    library = await get_or_404(session, Library, library_id, "知识库")
    library.deleted_at = datetime.now()
    await log(session, "delete", "library", library.id)
    await commit(session, "删除知识库失败")


@router.post("/libraries/{library_id}/restore", response_model=LibraryOut)
async def restore_library(library_id: int, session: AsyncSession = Depends(get_db)):
    library = await get_or_404(session, Library, library_id, "知识库")
    library.deleted_at = None
    await log(session, "restore", "library", library.id)
    await commit(session, "恢复知识库失败")
    await session.refresh(library)
    return library


@router.get("/libraries/{library_id}/members", response_model=list[MemberOut])
async def list_members(library_id: int, session: AsyncSession = Depends(get_db)):
    await get_or_404(session, Library, library_id, "知识库")
    return list((await session.execute(select(LibraryMember).where(LibraryMember.library_id == library_id))).scalars())


@router.post("/libraries/{library_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def add_member(library_id: int, payload: MemberCreate, session: AsyncSession = Depends(get_db)):
    await get_or_404(session, Library, library_id, "知识库")
    await get_or_404(session, User, payload.user_id, "用户")
    member = LibraryMember(library_id=library_id, **payload.model_dump())
    session.add(member)
    await session.flush()
    await log(session, "add_member", "library_member", f"{library_id}:{payload.user_id}", {"library_id": library_id, "user_id": payload.user_id, "access_level": payload.access_level})
    await commit(session, "该用户已经是知识库成员")
    await session.refresh(member)
    return member


@router.delete("/libraries/{library_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(library_id: int, user_id: int, session: AsyncSession = Depends(get_db)):
    member = await session.get(LibraryMember, {"library_id": library_id, "user_id": user_id})
    if member is None:
        raise HTTPException(404, "成员不存在")
    await session.delete(member)
    await commit(session, "移除成员失败")


async def document_tags(session: AsyncSession, document_id: int) -> list[str]:
    result = await session.execute(
        select(Tag.name).join(DocumentTag, DocumentTag.tag_id == Tag.id)
        .where(DocumentTag.document_id == document_id).order_by(Tag.name)
    )
    return list(result.scalars())


async def document_chunk_count(session: AsyncSession, document_id: int) -> int:
    return (await session.execute(select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document_id))).scalar_one()


@router.get("/documents", response_model=list[DocumentListOut])
async def list_documents(
    library_id: int | None = Query(None), include_deleted: bool = Query(False),
    session: AsyncSession = Depends(get_db),
):
    statement = select(Document, Library.name).join(Library).order_by(Document.id.desc())
    if library_id is not None:
        statement = statement.where(Document.library_id == library_id)
    if not include_deleted:
        statement = statement.where(Document.deleted_at.is_(None))
    rows = (await session.execute(statement)).all()
    return [
        document_out(item, chunk_count=await document_chunk_count(session, item.id),
                     tags=await document_tags(session, item.id), library_name=library_name)
        for item, library_name in rows
    ]


@router.post("/documents", response_model=DocumentListOut, status_code=status.HTTP_201_CREATED)
async def create_document(payload: DocumentCreate, session: AsyncSession = Depends(get_db)):
    library = await get_or_404(session, Library, payload.library_id, "知识库")
    if library.deleted_at is not None or library.status != "active":
        raise HTTPException(400, "知识库已删除或停用")
    document = Document(**payload.model_dump())
    session.add(document)
    library.document_count += 1
    await session.flush()
    await log(session, "create", "document", document.id)
    await commit(session, "创建文档失败")
    return document_out(document, library_name=library.name)


@router.post("/documents/upload", response_model=DocumentUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    library_id: int, file: UploadFile = File(...), uploaded_by: int | None = None,
    session: AsyncSession = Depends(get_db),
):
    library = await get_or_404(session, Library, library_id, "知识库")
    if library.deleted_at is not None or library.status != "active":
        raise HTTPException(400, "知识库已删除或停用")
    raw = await file.read()
    filename = Path(file.filename or "upload").name
    directory = Path("storage") / "uploads" / str(library_id)
    directory.mkdir(parents=True, exist_ok=True)
    stored = directory / f"{uuid4().hex}_{filename}"
    stored.write_bytes(raw)
    document = Document(
        library_id=library_id, title=Path(filename).stem or filename, original_filename=filename,
        storage_key=stored.as_posix(), mime_type=file.content_type, file_size=len(raw),
        file_hash=hashlib.sha256(raw).hexdigest(), uploaded_by=uploaded_by,
    )
    session.add(document)
    library.document_count += 1
    await session.flush()
    await log(session, "upload", "document", document.id)
    await commit(session, "上传文档失败")
    return document_out(document, library_name=library.name)


@router.get("/documents/{document_id}", response_model=DocumentDetailOut)
async def get_document(document_id: int, session: AsyncSession = Depends(get_db)):
    document = await get_or_404(session, Document, document_id, "文档")
    library = await get_or_404(session, Library, document.library_id, "知识库")
    return document_out(document, chunk_count=await document_chunk_count(session, document.id),
                        tags=await document_tags(session, document.id), library_name=library.name)


@router.patch("/documents/{document_id}", response_model=DocumentDetailOut)
async def update_document(document_id: int, payload: DocumentUpdate, session: AsyncSession = Depends(get_db)):
    document = await get_or_404(session, Document, document_id, "文档")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    await log(session, "update", "document", document.id)
    await commit(session, "更新文档失败")
    library = await get_or_404(session, Library, document.library_id, "知识库")
    return document_out(document, chunk_count=await document_chunk_count(session, document.id),
                        tags=await document_tags(session, document.id), library_name=library.name)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: int, session: AsyncSession = Depends(get_db)):
    document = await get_or_404(session, Document, document_id, "文档")
    if document.deleted_at is None:
        library = await get_or_404(session, Library, document.library_id, "知识库")
        library.document_count = max(0, library.document_count - 1)
    document.deleted_at = datetime.now()
    await log(session, "delete", "document", document.id)
    await commit(session, "删除文档失败")


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkOut])
async def list_document_chunks(document_id: int, session: AsyncSession = Depends(get_db)):
    await get_or_404(session, Document, document_id, "文档")
    result = await session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index)
    )
    return list(result.scalars())


@router.put("/documents/{document_id}/tags", response_model=DocumentDetailOut)
async def replace_document_tags(document_id: int, payload: DocumentTagsUpdate, session: AsyncSession = Depends(get_db)):
    document = await get_or_404(session, Document, document_id, "文档")
    names = list(dict.fromkeys(name.strip() for name in payload.tag_names if name.strip()))
    result = await session.execute(select(Tag).where(Tag.name.in_(names))) if names else None
    tags = {tag.name: tag for tag in result.scalars()} if result else {}
    for name in names:
        if name not in tags:
            tag = Tag(name=name)
            session.add(tag)
            await session.flush()
            tags[name] = tag
    await session.execute(DocumentTag.__table__.delete().where(DocumentTag.document_id == document_id))
    session.add_all([DocumentTag(document_id=document_id, tag_id=tags[name].id) for name in names])
    await log(session, "update_tags", "document", document.id)
    await commit(session, "更新文档标签失败")
    library = await get_or_404(session, Library, document.library_id, "知识库")
    return document_out(document, chunk_count=await document_chunk_count(session, document.id),
                        tags=names, library_name=library.name)


@router.get("/tags", response_model=list[TagOut])
async def list_tags(session: AsyncSession = Depends(get_db)):
    return list((await session.execute(select(Tag).order_by(Tag.name))).scalars())


@router.post("/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
async def create_tag(payload: TagCreate, session: AsyncSession = Depends(get_db)):
    tag = Tag(name=payload.name.strip())
    session.add(tag)
    await session.flush()
    await log(session, "create", "tag", tag.id, {"name": tag.name})
    await commit(session, "标签名称已存在")
    await session.refresh(tag)
    return tag


@router.patch("/tags/{tag_id}", response_model=TagOut)
async def update_tag(tag_id: int, payload: TagUpdate, session: AsyncSession = Depends(get_db)):
    tag = await get_or_404(session, Tag, tag_id, "标签")
    tag.name = payload.name.strip()
    await log(session, "update", "tag", tag.id, {"name": tag.name})
    await commit(session, "标签名称已存在")
    await session.refresh(tag)
    return tag


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: int, session: AsyncSession = Depends(get_db)):
    tag = await get_or_404(session, Tag, tag_id, "标签")
    await log(session, "delete", "tag", tag.id, {"name": tag.name})
    await session.delete(tag)
    await commit(session, "删除标签失败")


@router.get("/operation-logs", response_model=OperationLogPageOut)
async def list_operation_logs(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    user_id: int | None = Query(None), resource_type: str | None = Query(None),
    operation: str | None = Query(None), started_at: datetime | None = Query(None),
    ended_at: datetime | None = Query(None), session: AsyncSession = Depends(get_db),
):
    filters = []
    if user_id is not None: filters.append(OperationLog.user_id == user_id)
    if resource_type: filters.append(OperationLog.resource_type == resource_type)
    if operation: filters.append(OperationLog.operation == operation)
    if started_at: filters.append(OperationLog.created_at >= started_at)
    if ended_at: filters.append(OperationLog.created_at <= ended_at)
    statement = (
        select(OperationLog, User.display_name)
        .outerjoin(User, User.id == OperationLog.user_id)
        .where(*filters)
        .order_by(OperationLog.id.desc())
    )
    total = await session.scalar(select(func.count()).select_from(OperationLog).where(*filters)) or 0
    rows = (await session.execute(statement.offset((page - 1) * page_size).limit(page_size))).all()
    return {
        "items": [
            {
                "id": item.id,
                "user_id": item.user_id,
                "user_display_name": display_name,
                "operation": item.operation,
                "resource_type": item.resource_type,
                "resource_id": item.resource_id,
                "request_ip": item.request_ip,
                "detail": item.detail,
                "created_at": item.created_at,
            }
            for item, display_name in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }