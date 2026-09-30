from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.security import CAMPAIGN_CREATOR_ROLES, get_current_user, hash_password, require_roles
from app.database import get_db
from app.models import Department, EmployeeGroup, EmployeeGroupMember, User, UserRole
from app.schemas import (
    DepartmentCreate,
    DepartmentOut,
    GroupCreate,
    GroupOut,
    UserCreate,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/api", tags=["org"])


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Department).order_by(Department.name).all()


@router.post("/departments", response_model=DepartmentOut)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.MANAGEMENT)),
):
    dept = Department(name=payload.name, code=payload.code)
    db.add(dept)
    write_audit(db, actor_id=user.id, action="create_department", entity_type="department", detail=payload.name)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/users", response_model=list[UserOut])
def list_users(
    role: UserRole | None = None,
    department_id: int | None = None,
    leaders_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if department_id:
        q = q.filter(User.department_id == department_id)
    if leaders_only:
        q = q.filter(User.is_leader.is_(True))
    return q.order_by(User.full_name).all()


@router.post("/users", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.MANAGEMENT)),
):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    new_user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        department_id=payload.department_id,
        employee_code=payload.employee_code,
        is_leader=payload.is_leader,
        locale=payload.locale,
    )
    db.add(new_user)
    write_audit(db, actor_id=user.id, action="create_user", entity_type="user", detail=payload.email)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.MANAGEMENT)),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(target, k, v)
    write_audit(db, actor_id=actor.id, action="update_user", entity_type="user", entity_id=user_id)
    db.commit()
    db.refresh(target)
    return target


@router.get("/groups", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    groups = db.query(EmployeeGroup).order_by(EmployeeGroup.name).all()
    out = []
    for g in groups:
        out.append(
            GroupOut(
                id=g.id,
                name=g.name,
                department_id=g.department_id,
                member_ids=[m.user_id for m in g.members],
            )
        )
    return out


@router.post("/groups", response_model=GroupOut)
def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*CAMPAIGN_CREATOR_ROLES)),
):
    group = EmployeeGroup(name=payload.name, department_id=payload.department_id, created_by_id=user.id)
    db.add(group)
    db.flush()
    for uid in payload.member_ids:
        db.add(EmployeeGroupMember(group_id=group.id, user_id=uid))
    write_audit(db, actor_id=user.id, action="create_group", entity_type="group", detail=payload.name)
    db.commit()
    db.refresh(group)
    return GroupOut(
        id=group.id,
        name=group.name,
        department_id=group.department_id,
        member_ids=payload.member_ids,
    )
