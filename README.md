# American Analytics

A smart document analysis system that lets you upload PDFs and ask questions about them. It uses AI to understand what you're asking and finds the right information from your documents. Pretty straightforward - upload, ask, get answers.

---

## What It Does

**The basic idea**: You upload PDF files, then ask the system questions about them. Instead of searching manually, the AI reads through everything and gives you answers. It's like having a smart assistant who's read all your documents.

**Some cool features:**
- User accounts with login (secure with JWT tokens)
- Upload PDFs and it automatically processes them
- Ask questions in natural language - no complex queries needed
- System gets smarter if it doesn't find what you want on the first try (retry mechanism)
- Keep track of your questions and answers
- Rate answers to help improve the system

---

## System Architecture

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

## Data Flow Diagram

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


**Why the retry thing?**

Sometimes your question doesn't match the documents perfectly the first time. Instead of just giving up, the system tries asking the question in different ways. If it still can't find anything after 2 retries, it tells you "sorry, can't find that info" instead of making stuff up.

---

## Features

### Core Features
- **User Authentication**
  - User registration with password hashing (bcrypt)
  - JWT-based token authentication
  - Secure token generation and validation

- **Document Management**
  - PDF upload and processing
  - Automatic text extraction using PyPDFLoader
  - Document storage with metadata tracking
  - Document deletion capability

- **Intelligent Query Processing**
  - Query rewriting for improved retrieval
  - Vector-based semantic search
  - Document reranking for relevance
  - Context-aware answer generation

- **Chat Management**
  - Persistent chat history storage
  - Multi-turn conversation support
  - User message tracking

- **Feedback System**
  - User feedback on answers
  - Feedback storage and retrieval

---


## Tech Stack

**Server & API:**
- FastAPI (modern, fast Python framework)
- Uvicorn (runs the server)

**Databases:**
- SQLite (stores user accounts, documents, Q&A, feedback)
- Qdrant (vector database - super fast for searching by similarity)

**AI & Machine Learning:**
- Google Gemini 2.5 Flash (the LLM - understands questions and generates answers)
- Cohere (creates embeddings and ranks results)
- LangGraph (manages the workflow - keeps everything coordinated)

**PDF Processing:**
- PyPDF (reads PDFs)
- LangChain (handles text splitting smartly)

**Security:**
- JWT tokens (for safe login)
- Bcrypt (password hashing - keeps passwords secure)

---

##  Project Structure

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

##  API Endpoints

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

## The Smart Parts Explained

### Query Rewriter
When you ask a question, the system doesn't just search as-is. It gets Gemini to rephrase your question to be more likely to find matches in the documents. This handles natural language variations - if you ask "what's the topic?" vs "summarize the main point", it converts both to a consistent search query.

### Document Grading
After retrieving documents, instead of just taking whatever was found, the system asks "are these actually relevant?" for each one. If they're not relevant, it retries with a different question rewrite. This prevents hallucinations - the AI won't make up answers when it doesn't have the info.

### Retry Logic
If the first search doesn't find anything useful:
- **Attempt 1**: Initial question search
- **Attempt 2**: Rewrites and searches again
- **Attempt 3**: One more try
- **If still nothing**: Returns "Information not available" instead of guessing

This makes the system much more reliable.

### Conversation Memory
The system keeps track of your conversation history, so if you ask follow-up questions, it understands the context. It's not just answering individual questions in isolation.

---


## Database Structure

**Users Table:**
- Store usernames and hashed passwords

**Documents Table:**
- Keep track of uploaded PDFs
- File paths, upload times

**ChatHistory Table:**
- Every message in every conversation
- Helps with context in follow-up questions

**Answers Table:**
- All Q&A pairs
- When they were asked

**Feedback Table:**
- User ratings on answers
- Helps identify good vs bad responses

**Qdrant (Vector DB):**
- Stores document chunks as embeddings
- Organized for super-fast similarity search
---


##  Docker Deployment

Build and run with Docker:
```bash
docker build -t american-analytics .
docker run -p 8000:8000 --env-file .env american-analytics
```

---

##  Setup & Installation

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
 API Keys Required

Google Gemini API Key
https://aistudio.google.com/app/apikey

 Cohere API Key
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
you can test by using FastAPI swagger UI

---

