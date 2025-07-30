from sqlalchemy import Column, Integer, String

from app.internal.db import Base


class Document(Base):
    __tablename__ = "document"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)


# Include your models here, and they will automatically be created as tables in the database on start-up
