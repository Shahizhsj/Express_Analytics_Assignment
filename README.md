# American Analytics - AI-Powered Document Analysis System

A sophisticated FastAPI-based backend system that leverages LLMs and vector databases to enable intelligent document retrieval and analysis. The system processes PDF documents, generates embeddings, and uses RAG (Retrieval Augmented Generation) for accurate question answering.

---

## 📋 Table of Contents
- [System Architecture](#system-architecture)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)

---

## 🏗️ System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATION                                   │
│                     (Web/Mobile Frontend)                                    │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ HTTP/REST
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FASTAPI SERVER (main.py)                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        API Routes                                    │  │
│  │  • /register          (User Authentication)                         │  │
│  │  • /token             (Login & JWT Token Generation)                │  │
│  │  • /documents/upload  (PDF File Upload & Processing)               │  │
│  │  • /query/{query}     (Question Answering)                         │  │
│  │  • /documents        (List Documents)                              │  │
│  │  • /delete/{id}      (Delete Document)                            │  │
│  │  • /showanswers      (Show All Answers)                           │  │
│  │  • /givefeedback     (Store User Feedback)                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬─────────────────┬────────────────┬──────────────┘
                           │                 │                │
        ┌──────────────────┘                 │                └────────────────┐
        │                                    │                                 │
        ▼                                    ▼                                 ▼
┌──────────────────┐            ┌──────────────────────┐        ┌────────────────────┐
│  SQLite Database │            │  Vector Database     │        │  LLM Workflow      │
│                  │            │  (Qdrant)            │        │  (LangGraph)       │
│  • Users         │            │                      │        │                    │
│  • Documents     │            │  • Document Vectors  │        │  ┌──────────────┐  │
│  • Answers       │            │  • Metadata          │        │  │ Query        │  │
│  • Feedback      │            │  • Similarity Search │        │  │ Rewriter     │  │
│  • Chat History  │            │                      │        │  ├──────────────┤  │
└──────────────────┘            └──────────────────────┘        │  │ Document     │  │
                                                                 │  │ Retriever    │  │
                                                                 │  ├──────────────┤  │
                                                                 │  │ Filter Docs  │  │
                                                                 │  ├──────────────┤  │
                                                                 │  │ Generate     │  │
                                                                 │  │ Answer       │  │
                                                                 │  └──────────────┘  │
                                                                 └────────────────────┘
                                                                        │
                                                            ┌───────────┴──────────┐
                                                            ▼                      ▼
                                                    ┌─────────────────┐  ┌──────────────────┐
                                                    │ Google Gemini   │  │ Cohere Embeddings│
                                                    │ (LLM)           │  │ (Vector Space)   │
                                                    └─────────────────┘  └──────────────────┘
```

---

## 🔄 Data Flow Diagram

### Document Upload Flow
```
User Upload (PDF)
       │
       ▼
┌─────────────────────┐
│ FastAPI Endpoint    │
│ /documents/upload   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ PyPDFLoader         │  ← Extract text from PDF
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ RecursiveCharacter  │  ← Split into chunks
│ TextSplitter        │    (chunk_size: 1000)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Cohere Embeddings   │  ← Generate vector embeddings
│ (embed-v4.0)        │    (1024 dimensions)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Qdrant Vector DB    │  ← Store vectors with metadata
│ (documents)         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ SQLite Database     │  ← Store document metadata
│ (Documents table)   │
└─────────────────────┘
```

### Query Processing Flow (RAG Pipeline with Retry Mechanism)
```
User Question (retry_count = 0)
       │
       ▼
┌──────────────────────────┐
│ Query Rewriter           │  ← Gemini rewrites query
│ (Google Gemini)          │    for better retrieval
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Embedding Generation     │  ← Convert to vector
│ (Cohere embed-v4.0)      │    (search_query type)
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Vector Similarity Search │  ← Search in Qdrant
│ (Qdrant Collection)      │    (Top 10 documents)
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Document Reranking       │  ← Cohere rerank-v3.5
│ (Filter Top-2)           │    Keeps best matches
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Grade Documents          │  ← Gemini grades relevance
│ (Relevance Check)        │    Returns "relevant" or
│                          │    "irrelevant" per doc
└──────────┬───────────────┘
           │
           ▼
    ┌──────────────────┐
    │ Any relevant     │
    │ docs found?      │
    └──┬───────────┬───┘
       │           │
    YES│           │NO
       │           │
       │           ▼
       │      ┌─────────────────────┐
       │      │ Retry Count >= 2?   │
       │      └──┬────────────┬──────┘
       │         │            │
       │        NO            YES
       │         │            │
       │         ▼            ▼
       │    ┌────────────┐ ┌─────────┐
       │    │Increment  │ │ Generate │
       │    │Retry Count│ │ Answer   │
       │    │increment_│ │ with NO  │
       │    │retry() │ │ CONTEXT  │
       │    └──┬─────┘ └─────────┘
       │       │            │
       │       ▼            ▼
       │    ┌────────────┐   │
       │    │Rewrite     │   │
       │    │Query Again │   │
       │    │(Loop back) │   │
       │    └────────────┘   │
       │                     │
       └──────────┬──────────┘
                  │
                  ▼
      ┌──────────────────────────┐
      │ Generate Final Answer    │  ← Gemini generates answer
      │ with Context + History   │    using relevant docs +
      │ (generate_answer)        │    conversation history
      └──────────┬───────────────┘
                 │
                 ▼
      ┌──────────────────────────┐
      │ Store Results            │  ← Save to database
      │ • Answer in Answers DB   │
      │ • Chat History (Q & A)   │
      └──────────────────────────┘
```

**Retry Logic Details:**
- **Attempt 1 (retry_count=0)**: Initial query rewrite and search
- **Attempt 2 (retry_count=1)**: If no relevant docs found, rewrite query differently and retry
- **Attempt 3 (retry_count=2)**: Last retry attempt
- **Max Retries Reached (retry_count >= 2)**: If still no relevant docs, generate answer with "Information not available"

---

## ✨ Features

### Core Features
- **🔐 User Authentication**
  - User registration with password hashing (bcrypt)
  - JWT-based token authentication
  - Secure token generation and validation

- **📄 Document Management**
  - PDF upload and processing
  - Automatic text extraction using PyPDFLoader
  - Document storage with metadata tracking
  - Document deletion capability

- **🤖 Intelligent Query Processing**
  - Query rewriting for improved retrieval
  - Vector-based semantic search
  - Document reranking for relevance
  - Context-aware answer generation

- **💬 Chat Management**
  - Persistent chat history storage
  - Multi-turn conversation support
  - User message tracking

- **⭐ Feedback System**
  - User feedback on answers
  - Feedback storage and retrieval

---

## 🛠️ Technology Stack

### Backend Framework
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server

### Database
- **SQLite** - Relational database (user data, documents, answers)
- **Qdrant** - Vector database (document embeddings, similarity search)

### Authentication & Security
- **Python-Jose** - JWT token handling
- **Passlib** - Password hashing
- **BCrypt** - Secure password encryption

### AI/ML & NLP
- **Google Gemini 2.5 Flash** - Large Language Model
- **Cohere** - Embeddings and reranking
- **LangChain** - Document loading and text splitting
- **LangGraph** - Workflow orchestration

### Data Processing
- **PyPDF** - PDF text extraction
- **RecursiveCharacterTextSplitter** - Intelligent text chunking
- **FAISS/Qdrant** - Vector similarity search

### Additional Tools
- **Python-dotenv** - Environment variable management
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation

---

## 📁 Project Structure

```
American_analytics/
├── backend/
│   ├── main.py                 # FastAPI app & API routes
│   ├── config.py               # Configuration & client initialization
│   ├── database.py             # SQLAlchemy setup
│   ├── models.py               # Database models
│   ├── schemas.py              # Pydantic schemas
│   ├── langgraph_workflow.py   # RAG pipeline orchestration
│   ├── requirements.txt         # Python dependencies
│   ├── .env                    # Environment variables
│   ├── Dockerfile              # Docker configuration
│   └── uploads/                # Uploaded PDF files
├── README.md                   # This file
└── .gitignore
```

---

## 🔌 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register new user |
| POST | `/token` | Login & get JWT token |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents/upload` | Upload & process PDF |
| GET | `/documents` | List all documents |
| GET | `/delete/{id}` | Delete document & vectors |

### Query & Answers
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/query/{query}` | Ask question on documents |
| GET | `/showanswers` | Get all answers |
| POST | `/givefeedback` | Submit feedback on answer |

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Git

### Step 1: Clone & Navigate
```bash
cd /path/to/American_analytics/backend
```

### Step 2: Create Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
### API Keys Required

### Google Gemini API Key
https://aistudio.google.com/app/apikey

### Cohere API Key
https://dashboard.cohere.com/api-keys

Create a `.env` file with your API keys:
```
GOOGLE_API_KEY=your_google_gemini_api_key
COHERE_API_KEY=your_cohere_api_key
```

### Step 5: Run the Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at `http://localhost:8000`

### Step 6: Access API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📖 Usage

### 1. Register User
```bash
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "user1", "password": "password123"}'
```

### 2. Login & Get Token
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user1&password=password123"
```

### 3. Upload Document
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@document.pdf"
```

### 4. Ask Question
```bash
curl -X POST "http://localhost:8000/query/What%20is%20the%20main%20topic?" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. View Answers
```bash
curl -X GET "http://localhost:8000/showanswers" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 6. Submit Feedback
```bash
curl -X POST "http://localhost:8000/givefeedback" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"Id": "1", "feedback": "Answer was helpful"}'
```

---

## 🔑 Key Components Explanation

### 1. **config.py** - Central Configuration
- Initializes Google Gemini and Cohere clients
- Sets up Qdrant vector database
- Stores authentication secrets
- Creates upload directory

### 2. **models.py** - Database Schema
- **User**: Authentication & user management
- **Document**: PDF metadata
- **ChatHistory**: Conversation logs
- **Answers**: Q&A records
- **Feedback**: User ratings

### 3. **langgraph_workflow.py** - RAG Pipeline with Intelligent Retry

The workflow is a sophisticated 5-node LangGraph that implements adaptive query refinement:

#### **Workflow Nodes:**
1. **rewrite_query()** - Query optimization
   - Uses Gemini to rephrase user query for better retrieval
   - Improves semantic matching with stored documents

2. **retrieve_documents()** - Multi-step retrieval
   - Converts query to embedding (Cohere embed-v4.0, 1024 dims)
   - Searches Qdrant for top 10 similar documents
   - Reranks results with Cohere rerank-v3.5, keeps top 2 most relevant

3. **grade_documents()** - Relevance validation
   - **Critical Step**: Checks if retrieved documents are actually relevant
   - Uses Gemini to grade each document as "relevant" or "irrelevant"
   - Filters out low-quality matches

4. **route_after_grading()** - Intelligent routing
   - **IF** relevant docs found → proceed to answer generation
   - **IF** no relevant docs AND retry_count < 2 → retry with different query rewrite
   - **IF** retry_count >= 2 → proceed to answer generation anyway (with fallback message)

5. **generate_answer()** - Context-aware response
   - Uses filtered relevant documents as context
   - Includes chat history for multi-turn conversations
   - Falls back to "Information not available" if no context exists

#### **Retry Mechanism (Max 2 Retries):**
```
Attempt 1: rewrite_query() → retrieve_documents() → grade_documents()
         ↓ (No relevant docs found)
Attempt 2: increment_retry() → rewrite_query() → retrieve_documents() → grade_documents()
         ↓ (Still no relevant docs)
Attempt 3: increment_retry() → rewrite_query() → retrieve_documents() → grade_documents()
         ↓ (Max retries reached or docs found)
         → generate_answer() → END
```

**Why This Matters:**
- Handles edge cases where initial query doesn't match documents well
- Automatically reformulates questions to find relevant content
- Avoids hallucinations by grading relevance before answering
- Gracefully degrades when no matching documents exist

### 4. **main.py** - API Implementation
- FastAPI routes
- Request/response handling
- Document processing pipeline
- Authentication middleware

---

## 🔒 Security Considerations

- API keys stored in `.env` (never commit to repo)
- JWT authentication for protected routes
- Password hashing with bcrypt
- SQL injection prevention via SQLAlchemy ORM
- CORS should be configured for production

---

## 📈 Performance Considerations

- **Vector Database**: Qdrant for fast similarity search (O(log n))
- **Text Chunking**: 1000 tokens per chunk for balanced retrieval
- **Embedding Dimension**: 1024-dim vectors for rich semantic representation
- **Caching**: Consider caching frequent queries in production

---

## 🐳 Docker Deployment

Build and run with Docker:
```bash
docker build -t american-analytics .
docker run -p 8000:8000 --env-file .env american-analytics
```

---
