# Design Choices and Implementation Details

I added authentication to my FastAPI application. User details are stored in a database so that we can maintain chat history for each user. A possible improvement would be to maintain multiple chat sessions for each user instead of storing all conversations under a single chat history.

For the LLM, I used **Gemini 2.5 Flash**.

Regarding chunking, I used **RecursiveCharacterTextSplitter** with a **chunk size of 1000** and a **chunk overlap of 200**. These were my initial values, and my plan was to adjust them if I did not get relevant answers. Fortunately, the results were already accurate and relevant, so I did not need to modify them.

For embeddings, I used **Cohere Embeddings** because they are easy to integrate and provide good performance. I also used **chunk reranking**, which I had previously implemented in my assignment. The embedding dimension used is **1024**.

I chose **Qdrant** because it is easy to deploy, provides excellent metadata filtering capabilities for RAG applications, and is an open-source, production-ready vector database. It offers a good balance between simplicity and scalability compared to alternatives such as FAISS, ChromaDB, and Milvus.

These are the primary design choices I made for the RAG system.

When retrieving chunks from the vector database, I use a reranking model and keep only the top-k results. In my project, I keep only the **top 2 relevant chunks**. I experimented with different values such as 10, 7, and 5. I found that using only the top 2 chunks resulted in very little reduction in answer quality while significantly reducing latency. It also helped reduce the number of API calls and rate-limit issues. However, there is always a possibility of missing some relevant chunks. Therefore, I believe this value should be tuned based on the dataset and the model being used.

For the conditional branching logic, the reranked documents are passed to an LLM for relevance verification. If no relevant documents are found, the workflow returns to the query rewriting step. I set a maximum retry limit of **2 iterations**. If no relevant documents are found after two retries, the LLM responds with **"I do not know."**

I chose a retry limit of 2 because of API rate-limit constraints, and during testing this configuration performed well.

One improvement I could make is related to document filtering. Currently, I use both **chunk reranking** and **LLM-based relevance verification**. Since both methods serve a similar purpose, one of them could potentially be removed. I believe removing the reranker might simplify the pipeline, but keeping it helps retrieve more relevant chunks before they are passed to the LLM. This comes at the cost of increased latency but may improve answer accuracy.

# FastAPI Application

Although authentication was not required in the assignment, I implemented it because it helps manage users and their chat histories more effectively.

The application provides an **upload endpoint** through which users can upload documents. When a document is uploaded, the backend processes it through the following pipeline:

**Chunking → Embedding Generation → Storage in Vector Database**

There is also a **query endpoint** that allows users to ask questions about their uploaded documents. The LLM has access to previous conversations, enabling follow-up questions and multi-turn interactions.

To manage context size and token usage, I store only the **last five conversations** for each user. This value can be adjusted if necessary. I chose five conversations because including more history would increase token consumption without providing significant additional benefits in most cases.

The application also provides:

* A document listing endpoint to view uploaded documents.
* A document deletion endpoint that removes documents using their document ID.
* A feedback endpoint that allows users to submit feedback on generated answers.
* An endpoint to view previously submitted feedback.

# Database Design

I designed the database using five tables:

### 1. Users

Stores user information, including:

* User ID
* Username
* Hashed Password

### 2. Documents

Stores information about uploaded documents, including:

* Document ID
* Document Name
* Document Path
* Creation Time

### 3. ChatHistory

Stores conversation history for each user, including:

* User ID
* User Messages
* Assistant Responses

These conversations are retrieved and provided as context to the LLM, enabling conversational memory.

### 4. Answers

Stores:

* User Questions
* Generated Answers

Each answer is assigned a unique ID, which is later referenced by the Feedback table.

### 5. Feedback

Stores user feedback associated with a specific answer using the answer ID as a foreign key.

# Future Improvements

There is still significant room for improvement in the system. Some possible enhancements include:

* Simplifying the retrieval pipeline by removing either reranking or LLM-based relevance verification.
* Improving system prompts to better handle edge cases.
* Supporting multiple chat sessions per user.
* Experimenting with different chunk sizes and retrieval strategies.
* Implementing caching to reduce latency and API costs.
* Adding monitoring and evaluation metrics to measure retrieval and answer quality.

Overall, these are the major design decisions and trade-offs I made while building the RAG application.
