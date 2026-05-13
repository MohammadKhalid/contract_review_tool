from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database.connection import Base


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=True)  # Path where file is stored
    file_size = Column(Integer, nullable=True)  # File size in bytes
    mime_type = Column(String, nullable=True)
    upload_date = Column(DateTime, default=datetime.utcnow)
    processing_method = Column(
        String, nullable=True
    )  # 'text_extraction', 'ocr', or 'ocr_fallback'

    # Relationship to analysis results
    analyses = relationship(
        "ContractAnalysis", back_populates="contract", cascade="all, delete-orphan"
    )


class ContractAnalysis(Base):
    __tablename__ = "contract_analyses"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    analysis_date = Column(DateTime, default=datetime.utcnow)

    # Extracted text content
    extracted_text = Column(Text, nullable=True)

    # Analysis results stored as JSON
    word_count = Column(Integer, nullable=True)
    sentence_count = Column(Integer, nullable=True)
    key_terms = Column(JSON, nullable=True)  # List of found key terms
    named_entities = Column(JSON, nullable=True)  # List of named entities
    potential_issues = Column(JSON, nullable=True)  # List of potential issues

    # Processing metadata
    processing_time_seconds = Column(Integer, nullable=True)
    ocr_used = Column(String, nullable=True)  # 'none', 'primary', 'fallback'

    # Relationship back to contract
    contract = relationship("Contract", back_populates="analyses")
