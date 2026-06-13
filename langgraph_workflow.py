from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from config import google_client, co, client


# State definition
class GraphState(TypedDict):
    question: str
    rewritten_query: str
    retrieved_docs: List[str]
    filtered_docs: List[str]
    answer: str
    history: str
    retry_count: int


# Node functions
def rewrite_query(state: GraphState):
    """Rewrite the user's query to improve document retrieval."""
    prompt = f"""
    Rewrite the query to improve document retrieval.

    Query:
    {state['question']}

    Return only the rewritten query.
    """

    response = google_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return {
        "rewritten_query": response.text
    }


def retrieve_documents(state: GraphState):
    """Retrieve relevant documents using vector search and reranking."""
    query = state["rewritten_query"]

    query_embedding = co.embed(
        texts=[query],
        model="embed-v4.0",
        input_type="search_query",
        output_dimension=1024,
        embedding_types=["float"],
    ).embeddings.float[0]

    results = client.query_points(
        collection_name="documents",
        query=query_embedding,
        limit=10
    )

    documents = [
        point.payload["text"]
        for point in results.points
    ]

    rerank_results = co.rerank(
        model="rerank-v3.5",
        query=query,
        documents=documents,
        top_n=2
    )

    top_chunks = []

    for result in rerank_results.results:
        top_chunks.append(
            documents[result.index]
        )

    return {
        "retrieved_docs": top_chunks
    }


def grade_documents(state: GraphState):
    """Grade retrieved documents for relevance using LLM."""
    query = state["question"]
    
    relevant_docs = []
    for doc in state["retrieved_docs"]:

        prompt = f"""
        Question:
        {query}

        Document:
        {doc}

        Is this document relevant
        to answer the question?

        Reply ONLY:

        relevant

        OR

        irrelevant
        """

        response = google_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        grade = response.text.strip().lower()

        if grade == "relevant":
            relevant_docs.append(doc)


    return {
        "filtered_docs": relevant_docs
    }


def route_after_grading(state: GraphState):
    """Decide next step based on grading results."""
    docs = state["filtered_docs"]
    retries = state.get("retry_count", 0)

    if len(docs) > 0:
        return "generate"

    if retries >= 2:
        return "end"

    return "rewrite"


def increment_retry(state: GraphState):
    """Increment retry counter for query rewriting."""
    return {
        "retry_count": state.get("retry_count", 0) + 1
    }


def generate_answer(state: GraphState):
    """Generate final answer using context and conversation history."""
    context = "\n\n".join(
        state["filtered_docs"]
    )

    prompt = f"""
You are a helpful AI assistant.

Conversation History:
{state["history"]}

Retrieved Context:
{context}

User Question:
{state["question"]}

Instructions:
- Answer only using context.
- Use history if relevant.
- If answer not found say:
  "Information not available."

Answer:
"""

    response = google_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return {
        "answer": response.text
    }


# Build workflow
def build_workflow():
    """Create and compile the LangGraph workflow."""
    workflow = StateGraph(GraphState)

    workflow.add_node("rewrite", rewrite_query)
    workflow.add_node("retrieve", retrieve_documents)
    workflow.add_node("grade", grade_documents)
    workflow.add_node("generate", generate_answer)
    workflow.add_node("retry", increment_retry)

    workflow.set_entry_point("rewrite")

    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("retrieve", "grade")
    workflow.add_conditional_edges(
        "grade",
        route_after_grading,
        {
            "generate": "generate",
            "rewrite": "retry",
            "end": END
        }
    )
    workflow.add_edge("retry", "rewrite")
    workflow.add_edge("generate", END)

    return workflow.compile()


# Create the compiled graph
graph = build_workflow()
