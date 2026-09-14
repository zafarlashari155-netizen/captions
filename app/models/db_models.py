import datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    google_sub = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    is_subscribed = Column(Boolean, default=False, nullable=False)
    stripe_customer_id = Column(String, nullable=True, index=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")


class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (UniqueConstraint("user_id", "usage_date", "job_id", name="uq_usage_user_date_job"),)
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    usage_date = Column(Date, default=datetime.date.today, index=True, nullable=False)
    job_id = Column(String, nullable=False, index=True)
    user = relationship("User", back_populates="usage_records")
