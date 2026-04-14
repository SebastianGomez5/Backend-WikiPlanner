import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Time, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    google_refresh_token = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


    settings = relationship("UserSettings", back_populates="user", uselist=False)
    tasks = relationship("Task", back_populates="user")
    time_blocks = relationship("TimeBlock", back_populates="user")
    decision_history = relationship("DecisionHistory", back_populates="user")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    current_mode = Column(String, nullable=True)
    work_start_time = Column(Time, nullable=True)
    work_end_time = Column(Time, nullable=True)
    preferences = Column(JSONB, nullable=True)

    user = relationship("User", back_populates="settings")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    priority = Column(Integer, nullable=False)
    difficulty_level = Column(String, nullable=True)
    category = Column(String, nullable=True)
    energy_level = Column(String, nullable=True)
    is_flexible = Column(Boolean, default=True)
    deadline = Column(DateTime, nullable=True)
    status = Column(String, default="Pendiente")

    user = relationship("User", back_populates="tasks")
    time_blocks = relationship("TimeBlock", back_populates="task")


class TimeBlock(Base):
    __tablename__ = "time_blocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    google_event_id = Column(String, nullable=True)
    is_locked = Column(Boolean, default=False)

    user = relationship("User", back_populates="time_blocks")
    task = relationship("Task", back_populates="time_blocks")


class DecisionHistory(Base):
    __tablename__ = "decision_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    conflict_context = Column(JSONB, nullable=False)
    ai_suggested_action = Column(String, nullable=False)
    user_final_action = Column(String, nullable=True)
    is_accepted = Column(Boolean, nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="decision_history")