from typing import Generator

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    Session,
    sessionmaker,
)

# Database
DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


# Base Model
class Base(DeclarativeBase):
    pass


# Database Table
class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(80),
        nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
        nullable=False
    )
    age: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Task 4 - FastAPI + SQLite",
    version="1.0.0"
)


# Pydantic Models
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(
        min_length=5,
        max_length=120,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )
    age: int = Field(ge=13, le=120)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    email: str | None = Field(
        default=None,
        min_length=5,
        max_length=120,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )
    age: int | None = Field(default=None, ge=13, le=120)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    age: int

    model_config = {"from_attributes": True}


# Database Session
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Root Endpoint
@app.get("/")
def root():
    return {
        "message": "Task 4 database API is running",
        "database": "SQLite",
        "docs": "/docs"
    }


# Create User
@app.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db)
):
    existing = db.scalar(
        select(UserRow).where(UserRow.email == payload.email)
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Email already exists"
        )

    row = UserRow(**payload.model_dump())

    db.add(row)
    db.commit()
    db.refresh(row)

    return row


# List Users
@app.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(UserRow).order_by(UserRow.id)
        ).all()
    )


# Get User
@app.get("/users/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    row = db.get(UserRow, user_id)

    if not row:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return row


# Update User
@app.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db)
):
    row = db.get(UserRow, user_id)

    if not row:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    changes = payload.model_dump(exclude_unset=True)

    if (
        changes.get("email")
        and changes["email"] != row.email
    ):
        existing = db.scalar(
            select(UserRow).where(
                UserRow.email == changes["email"]
            )
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Email already exists"
            )

    for key, value in changes.items():
        if value is not None:
            setattr(row, key, value)

    db.commit()
    db.refresh(row)

    return row


# Delete User
@app.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    row = db.get(UserRow, user_id)

    if not row:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    db.delete(row)
    db.commit()

    return {
        "message": f"User {user_id} deleted"
    }