from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    raw_description = Column(Text, nullable=False)
    rubric_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    resumes = relationship("Resume", back_populates="job")
    scores = relationship("Score", back_populates="job")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    filename = Column(String, nullable=False)
    raw_text = Column(Text)
    parsed_json = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="resumes")
    scores = relationship("Score", back_populates="resume")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    total_score = Column(Integer, nullable=False)
    criteria_breakdown_json = Column(Text, nullable=False)
    justification_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    resume = relationship("Resume", back_populates="scores")
    job = relationship("Job", back_populates="scores")