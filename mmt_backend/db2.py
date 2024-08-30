from datetime import datetime
from typing import List

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class User(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    locale: Mapped[str] = mapped_column(String(2), nullable=False, default="en")
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    can_upload: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    uploads: Mapped[List["Upload"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"User(username={self.username})"


class Upload(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="uploads")
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, default=datetime.utcnow
    )
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="created")
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transferred: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_type: Mapped[str] = mapped_column(
        String(255), nullable=False, default="text/plain"
    )
    checksum_server: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    checksum_client: Mapped[str] = mapped_column(String(32), nullable=False, default="")


class Job(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column()
    intended_use: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[str] = mapped_column(String(255), nullable=False)
    # The following do not work for models at all, just jobs.
    language: Mapped[str] = mapped_column(String(3), nullable=False)
    speaker_count: Mapped[int] = mapped_column(Integer, nullable=False)
