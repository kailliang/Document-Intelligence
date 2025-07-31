from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional


# ===================================================================
# DocumentVersion相关的Pydantic模式
# ===================================================================

class DocumentVersionBase(BaseModel):
    """
    DocumentVersion的基础模式 - 包含版本的基本信息
    
    为什么要分Base, Create, Read模式？
    - Base: 共同字段，其他模式继承它
    - Create: 创建版本时需要的字段
    - Read: 从数据库读取时返回的字段（包含ID、时间戳等）
    """
    content: str
    version_number: int


class DocumentVersionCreate(DocumentVersionBase):
    """创建新版本时使用的模式"""
    pass


class DocumentVersionRead(DocumentVersionBase):
    """从数据库读取版本时返回的模式"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    document_id: int
    is_active: bool
    created_at: datetime


# ===================================================================
# Document相关的Pydantic模式
# ===================================================================

class DocumentBase(BaseModel):
    """Document的基础模式"""
    title: str


class DocumentCreate(DocumentBase):
    """创建新文档时使用的模式"""
    pass


class DocumentRead(DocumentBase):
    """
    从数据库读取文档时返回的模式
    
    为什么包含versions？
    - 让前端能够获取文档的所有版本历史
    - Optional[List[...]] 表示可选的版本列表
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    current_version_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    # 包含所有版本的列表 - 用于版本历史显示
    versions: Optional[List[DocumentVersionRead]] = []
    
    # 当前激活版本的详细信息
    current_version: Optional[DocumentVersionRead] = None


# ===================================================================
# API请求/响应的专用模式
# ===================================================================

class DocumentWithCurrentVersion(BaseModel):
    """
    返回文档及其当前版本内容的专用模式
    这个模式专门用于编辑器，只返回必要的信息
    """
    id: int
    title: str
    content: str  # 当前版本的内容
    version_number: int  # 当前版本号
    last_modified: datetime


class CreateVersionRequest(BaseModel):
    """创建新版本的请求模式"""
    content: str


class SwitchVersionRequest(BaseModel):
    """切换版本的请求模式"""
    version_number: int
