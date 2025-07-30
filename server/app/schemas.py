from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    content: str


class DocumentRead(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
