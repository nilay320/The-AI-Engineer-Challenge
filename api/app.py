# Import required FastAPI components for building the API
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
# Import Pydantic for data validation and settings management
from pydantic import BaseModel
# Import OpenAI client for interacting with OpenAI's API
from openai import OpenAI
import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import json
import PyPDF2
import io
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Initialize FastAPI application with a title
app = FastAPI(title="OpenAI Chat API with RAG")

# Configure CORS (Cross-Origin Resource Sharing) middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the data model for chat requests using Pydantic
class ChatRequest(BaseModel):
    developer_message: str
    user_message: str
    model: Optional[str] = "gpt-4.1-mini"

class RAGChatRequest(BaseModel):
    user_message: str
    use_rag: bool = True

# Load environment variables from .env file
load_dotenv()

# Global RAG variables
qdrant_client = None
collection_name = "startup_docs"
vector_size = 1536
documents = {}

def init_rag():
    """Initialize RAG components."""
    global qdrant_client
    try:
        qdrant_client = QdrantClient(":memory:")
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        print("RAG initialized successfully")
    except Exception as e:
        print(f"RAG initialization error: {e}")

def get_embedding(text: str, client: OpenAI) -> List[float]:
    """Get embedding for text using OpenAI."""
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Embedding error: {e}")
        return [0.0] * vector_size

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        pdf_file = io.BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        if end > len(text):
            end = len(text)
        
        chunk = text[start:end]
        chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def validate_content(text: str) -> Dict[str, Any]:
    """Simple content validation for startup/business documents."""
    business_keywords = [
        'startup', 'business', 'company', 'entrepreneur', 'venture', 'funding',
        'investment', 'revenue', 'profit', 'market', 'customer', 'product',
        'service', 'strategy', 'business plan', 'pitch', 'investor', 'valuation',
        'growth', 'scale', 'team', 'founder', 'CEO', 'financial', 'marketing',
        'sales', 'operations', 'model', 'vision', 'mission', 'goals'
    ]
    
    text_lower = text.lower()
    keyword_count = sum(1 for keyword in business_keywords if keyword in text_lower)
    
    is_valid = keyword_count >= 3
    
    return {
        "is_valid": is_valid,
        "keyword_count": keyword_count,
        "reason": f"Found {keyword_count} business keywords"
    }

def query_documents(query: str, client: OpenAI, top_k: int = 5) -> List[Dict[str, Any]]:
    """Query documents for relevant chunks."""
    try:
        if not qdrant_client:
            return []
            
        query_embedding = get_embedding(query, client)
        
        search_results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=top_k
        )
        
        results = []
        for result in search_results:
            results.append({
                "text": result.payload["text"],
                "filename": result.payload["filename"],
                "score": result.score,
                "chunk_index": result.payload["chunk_index"]
            })
        
        return results
        
    except Exception as e:
        print(f"Query error: {e}")
        return []

# Initialize RAG on startup
init_rag()

# Define the main chat endpoint that handles POST requests
@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured in backend.")
        client = OpenAI(api_key=api_key)
        
        async def generate():
            stream = client.chat.completions.create(
                model=request.model,
                messages=[
                    {"role": "developer", "content": request.developer_message},
                    {"role": "user", "content": request.user_message}
                ],
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        return StreamingResponse(generate(), media_type="text/plain")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# RAG Chat endpoint with streaming response
@app.post("/api/rag-chat")
async def rag_chat(request: RAGChatRequest):
    """Enhanced chat endpoint that uses RAG with uploaded documents."""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured in backend.")
        client = OpenAI(api_key=api_key)
        
        async def generate():
            try:
                # Get relevant documents
                relevant_docs = query_documents(request.user_message, client, 5)
                
                if not relevant_docs:
                    yield "I don't have any relevant documents to answer your question."
                    return
                
                # Create context
                context = "\n\n".join([doc["text"] for doc in relevant_docs])
                
                # Create prompt
                prompt = f"""You are a helpful startup mentor AI. Use the following context from uploaded business documents to answer the user's question.

Context:
{context}

Question: {request.user_message}

Answer:"""
                
                # Stream response
                stream = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful startup mentor AI assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True,
                    max_tokens=500,
                    temperature=0.7
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                        
            except Exception as e:
                yield f"Error: {str(e)}"

        return StreamingResponse(generate(), media_type="text/plain")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Chat error: {str(e)}")

# PDF Upload endpoint
@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file for RAG."""
    try:
        if not qdrant_client:
            raise HTTPException(status_code=500, detail="RAG service not initialized")
            
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
        # Check file size (limit to 5MB)
        max_size = 5 * 1024 * 1024
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="File size exceeds 5MB limit.")
        
        # Extract text
        text = extract_text_from_pdf(file_content)
        if not text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Validate content
        validation = validate_content(text)
        if not validation["is_valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Document doesn't contain enough business content. {validation['reason']}"
            )
        
        # Get OpenAI client
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured.")
        client = OpenAI(api_key=api_key)
        
        # Chunk text
        chunks = chunk_text(text)
        
        # Add chunks to vector database
        points = []
        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk, client)
            point = PointStruct(
                id=f"{file.filename}_{i}",
                vector=embedding,
                payload={
                    "text": chunk,
                    "filename": file.filename,
                    "chunk_index": i
                }
            )
            points.append(point)
        
        # Upsert points
        qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )
        
        # Store document info
        documents[file.filename] = {
            "total_chunks": len(chunks),
            "validation": validation
        }
        
        return {
            "success": True,
            "document_id": file.filename,
            "filename": file.filename,
            "total_chunks": len(chunks),
            "chunks_added": len(chunks),
            "text_preview": text[:200] + "..." if len(text) > 200 else text,
            "message": f"Successfully processed {file.filename} with {len(chunks)} chunks"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing error: {str(e)}")

# Get database statistics
@app.get("/api/rag-stats")
async def get_rag_stats():
    """Get statistics about the current RAG database."""
    try:
        if not qdrant_client:
            return {"error": "RAG service not initialized"}
            
        collection_info = qdrant_client.get_collection(collection_name)
        return {
            "total_documents": len(documents),
            "total_chunks": collection_info.points_count,
            "documents": list(documents.keys())
        }
    except Exception as e:
        return {"error": str(e)}

# Clear the RAG database
@app.delete("/api/rag-clear")
async def clear_rag_database():
    """Clear all documents from the RAG database."""
    try:
        if not qdrant_client:
            return {"success": False, "error": "RAG service not initialized"}
            
        qdrant_client.delete_collection(collection_name)
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        documents.clear()
        return {"success": True, "message": "Database cleared"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Query documents endpoint
@app.post("/api/query-documents")
async def query_documents_endpoint(request: dict):
    """Query the vector database for relevant documents."""
    try:
        query = request.get("query", "")
        top_k = request.get("top_k", 5)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query parameter is required.")
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured.")
        client = OpenAI(api_key=api_key)
        
        result = query_documents(query, client, top_k)
        return {"results": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "rag_initialized": qdrant_client is not None}

# Entry point for running the application directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 