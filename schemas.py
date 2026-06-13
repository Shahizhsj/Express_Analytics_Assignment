from pydantic import BaseModel
class UserCreate(BaseModel):
    username: str
    password: str

class Feedcreate(BaseModel):
    Id:str
    feedback:str