from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from schemas import UserCreate
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
import os
from schemas import Feedcreate
import uuid
from models import Answers,Feedback,ChatHistory
from sqlalchemy import desc
from models import Document
from database import session_local, engine
import models as models
from fastapi import FastAPI, Depends, HTTPException
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from config import (
    google_client, co, client, 
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    UPLOAD_DIR
)
from langgraph_workflow import graph

app = FastAPI()
models.Base.metadata.create_all(engine)

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token"
)
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(password, hashed):
    return pwd_context.verify(password, hashed)

def get_user_by_username(db: Session, username: str):
    """Fetch user by username - reusable function to avoid duplication."""
    return (
        db.query(models.User)
        .filter(models.User.username == username)
        .first()
    )

def unauthorized_exception():
    """Raise unauthorized exception - consistent error handling."""
    raise HTTPException(status_code=401, detail="Invalid credentials")

def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update(
        {"exp": expire}
    )

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )



def ingest(pdf_path):
    loader=PyPDFLoader(pdf_path)
    documents=loader.load()
    text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
    chunks=text_splitter.split_documents(documents)
    return chunks




def create_vector_store(chunks):
    model = "embed-v4.0"    
    input_type = "search_document"
    # Extract text content from LangChain document objects
    texts = [chunk.page_content for chunk in chunks]
    res = co.embed(
    texts=texts,
    model=model,
    input_type=input_type,
    output_dimension=1024,
    embedding_types=["float"],
    )
    return res.embeddings.float
    

def create_vector_db(chunks, embeddings,document_id):
    points=[]
    for chunk,embedding in zip(chunks,embeddings):
        point=PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "document_id":document_id,
                "text":chunk.page_content
            }
        )
        points.append(point)
    client.upsert(
        collection_name="documents",
        points=points
    )
    
def save_chat_history(user_id:str,role:str,message:str,db:Session):
    chat_history=models.ChatHistory(
        user_id=user_id,
        role=role,
        message=message
    )
    db.add(chat_history)
    db.commit()
    db.refresh(chat_history)

def get_last_10_messages(db,user_id: str):
    messages = (
        db.query(models.ChatHistory)
        .filter(models.ChatHistory.user_id == user_id)
        .order_by(desc(models.ChatHistory.created_at))
        .limit(5)
        .all()
    )

    return list(reversed(messages))

def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

    except JWTError:
        unauthorized_exception()

    user = get_user_by_username(db, username)
    
    if not user:
        unauthorized_exception()

    return user

@app.post("/register")
def register(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    db_user = models.User(
        username=user.username,
        hashed_password=get_password_hash(
            user.password
        )
    )

    db.add(db_user)
    db.commit()

    return {
        "message": "User created"
    }


@app.post("/token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    user = get_user_by_username(db, form_data.username)

    if not user:
        unauthorized_exception()

    if not verify_password(form_data.password, user.hashed_password):
        unauthorized_exception()

    token = create_access_token({"sub": user.username})

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    document = Document(
        filename=file.filename,
        file_path=file_path
    )

    db.add(document)
    db.commit()
    db.refresh(document)
    chunks=ingest(file_path)
    embeddings=create_vector_store(chunks)
    create_vector_db(chunks, embeddings, document.id)


    return {
        "message": "File uploaded successfully",
        "document_id": document.id,
        "chunks":chunks,
        "embeddings":embeddings
    }



@app.post("/query/{query}")
async def query_documents(
    query: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    history = get_last_10_messages(
        db,
        current_user.username
    )

    result = graph.invoke(
        {
            "question": query,
             "history": history,
            "retry_count": 0
        }
    )

    answer = result["answer"]

    save_chat_history(
        current_user.username,
        "user",
        query,
        db
    )
    answer_record = Answers(
        question=query,
        answer=answer
    )
    db.add(answer_record)
    db.commit()

    save_chat_history(
        current_user.username,
        "assistant",
        answer,
        db
    )

    return {
        "result": answer
    }    

@app.get("/documents")
async def list_documents(db: Session=Depends(get_db), current_user = Depends(get_current_user)):
    documents=db.query(Document).all()
    return {
        'message':"Documents retrieved successfully",
        'documents':documents
    }



@app.get('/delete/{id}')
async def delete_document(id:int,db:Session=Depends(get_db), current_user = Depends(get_current_user)):
    client.delete(
    collection_name="documents",
    points_selector=Filter(must=[FieldCondition(key="document_id",match=MatchValue(value=id))]))


    document=db.query(Document).filter(Document.id==id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        os.remove(document.file_path)
    except Exception as e:
        print(f"Error deleting file: {e}")
    
    db.delete(document)
    db.commit()
    
    return {
        "message": "Document deleted successfully"
    }

@app.get('/showanswers')
async def showanswers(db:Session=Depends(get_db), current_user = Depends(get_current_user)):
    anwers=db.query(Answers).all()
    return {
        'Answers':anwers
    }

@app.post('/givefeedback')
async def Give_feedback(feedback_data: Feedcreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    answer=db.query(Answers).filter(Answers.id==feedback_data.Id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    feedback = Feedback(
        answer_id=feedback_data.Id,
        feedback=feedback_data.feedback
    )
    db.add(feedback)
    db.commit()
    
    return {
        "message": "Feedback added successfully"
    }
