from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.internal.db import Base


class Document(Base):
    """
    文档主表 - 存储文档的基本信息和元数据
    
    为什么要分离Document和DocumentVersion？
    - Document: 存储文档的基本信息（标题、当前版本等）
    - DocumentVersion: 存储每个版本的具体内容
    这样设计让版本管理更清晰，也便于后续扩展功能
    """
    __tablename__ = "document"
    
    # 主键ID
    id = Column(Integer, primary_key=True, index=True)
    
    # 文档标题 - 用户友好的文档名称
    title = Column(String, nullable=False, default="Untitled Document")
    
    # 当前活跃版本ID - 指向用户当前查看/编辑的版本
    current_version_id = Column(Integer, ForeignKey("document_version.id"), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系定义 - SQLAlchemy的ORM功能
    # back_populates 创建双向关系，让我们可以从Document访问versions，也可以从Version访问document
    # foreign_keys 明确指定哪个外键用于这个关系，避免歧义
    versions = relationship(
        "DocumentVersion", 
        back_populates="document", 
        cascade="all, delete-orphan",
        foreign_keys="DocumentVersion.document_id"  # 明确指定外键
    )
    
    # 当前版本的关系 - 单独定义便于快速访问当前版本
    current_version = relationship(
        "DocumentVersion", 
        foreign_keys=[current_version_id], 
        post_update=True
    )


class DocumentVersion(Base):
    """
    文档版本表 - 存储每个版本的具体内容和版本信息
    
    为什么需要version_number？
    - 给用户看的版本号（v1.0, v2.0等）
    - 比数据库ID更友好和有意义
    
    为什么需要is_active？
    - 标记哪个版本是当前激活的版本
    - 允许用户在不同版本间切换
    """
    __tablename__ = "document_version"
    
    # 主键ID
    id = Column(Integer, primary_key=True, index=True)
    
    # 外键 - 关联到哪个文档
    document_id = Column(Integer, ForeignKey("document.id"), nullable=False, index=True)
    
    # 版本号 - 从1开始递增（v1.0, v2.0...）
    version_number = Column(Integer, nullable=False)
    
    # 版本内容 - 这个版本的实际文档内容
    content = Column(String, nullable=False, default="")
    
    # 是否是当前激活版本
    is_active = Column(Boolean, default=False, nullable=False)
    
    # 创建时间 - 记录这个版本何时创建
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 关系定义 - 反向关系到Document
    document = relationship("Document", back_populates="versions", foreign_keys=[document_id])


# Include your models here, and they will automatically be created as tables in the database on start-up
