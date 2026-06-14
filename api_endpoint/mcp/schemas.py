from pydantic import BaseModel

class ImageBytesRequest(BaseModel):
    image_base64: str

class PreviewRequest(BaseModel):
    image_base64: str