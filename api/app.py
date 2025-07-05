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
        # Truncate text if too long to prevent API errors
        max_length = 8000  # Conservative limit for OpenAI embeddings
        if len(text) > max_length:
            text = text[:max_length]
            print(f"⚠️ Truncated text to {max_length} characters for embedding")
        
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text.strip()
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Embedding error for text length {len(text)}: {e}")
        # Return zero vector as fallback
        return [0.0] * vector_size

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        print(f"🔍 Processing PDF of {len(file_bytes)} bytes")
        pdf_file = io.BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        print(f"📄 PDF has {len(pdf_reader.pages)} pages")
        
        # Limit pages to prevent memory issues
        max_pages = 20
        pages_to_process = min(len(pdf_reader.pages), max_pages)
        if len(pdf_reader.pages) > max_pages:
            print(f"⚠️ Limiting to first {max_pages} pages to prevent memory issues")
        
        text = ""
        for i in range(pages_to_process):
            try:
                page_text = pdf_reader.pages[i].extract_text()
                if page_text:
                    text += page_text + "\n"
                print(f"✅ Processed page {i+1}/{pages_to_process}")
            except Exception as e:
                print(f"⚠️ Error extracting page {i+1}: {e}")
                continue
        
        print(f"✅ Extracted {len(text)} characters from {pages_to_process} pages")
        return text.strip()
        
    except Exception as e:
        print(f"❌ PDF extraction error: {e}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

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
        print(f"📄 Starting PDF upload: {file.filename}")
        
        if not qdrant_client:
            print("❌ RAG service not initialized")
            raise HTTPException(status_code=500, detail="RAG service not initialized")
            
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            print("❌ Invalid file type")
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
        # Check file size (limit to 5MB)
        max_size = 5 * 1024 * 1024
        file_content = await file.read()
        print(f"📁 File size: {len(file_content)} bytes")
        
        if len(file_content) > max_size:
            print("❌ File too large")
            raise HTTPException(status_code=400, detail="File size exceeds 5MB limit.")
        
        # Extract text with better error handling
        print("🔍 Extracting text from PDF...")
        try:
            text = extract_text_from_pdf(file_content)
            if not text or len(text.strip()) < 10:
                print("❌ No text extracted")
                raise HTTPException(status_code=400, detail="Could not extract meaningful text from PDF")
            print(f"✅ Extracted {len(text)} characters")
        except Exception as e:
            print(f"❌ PDF extraction failed: {e}")
            raise HTTPException(status_code=400, detail=f"PDF extraction failed: {str(e)}")
        
        # Validate content
        print("🤖 Validating content...")
        try:
            validation = validate_content(text)
            if not validation["is_valid"]:
                print(f"❌ Content validation failed: {validation['reason']}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Document doesn't contain enough business content. {validation['reason']}"
                )
            print(f"✅ Content validation passed: {validation['reason']}")
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Content validation error: {e}")
            raise HTTPException(status_code=500, detail=f"Content validation error: {str(e)}")
        
        # Get OpenAI client
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("❌ No OpenAI API key")
            raise HTTPException(status_code=500, detail="OpenAI API key not configured.")
        
        try:
            client = OpenAI(api_key=api_key)
            print("✅ OpenAI client initialized")
        except Exception as e:
            print(f"❌ OpenAI client error: {e}")
            raise HTTPException(status_code=500, detail=f"OpenAI client error: {str(e)}")
        
        # Chunk text
        print("✂️ Chunking text...")
        try:
            chunks = chunk_text(text)
            print(f"✅ Created {len(chunks)} chunks")
            
            # Limit chunks to prevent memory issues
            if len(chunks) > 50:
                chunks = chunks[:50]
                print(f"⚠️ Limited to first 50 chunks to prevent memory issues")
                
        except Exception as e:
            print(f"❌ Text chunking error: {e}")
            raise HTTPException(status_code=500, detail=f"Text processing error: {str(e)}")
        
        # Process chunks in smaller batches to avoid memory issues
        print("🧠 Generating embeddings...")
        points = []
        batch_size = 10  # Process 10 chunks at a time
        
        try:
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                print(f"Processing batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")
                
                for j, chunk in enumerate(batch_chunks):
                    try:
                        embedding = get_embedding(chunk, client)
                        point = PointStruct(
                            id=f"{file.filename}_{i + j}",
                            vector=embedding,
                            payload={
                                "text": chunk,
                                "filename": file.filename,
                                "chunk_index": i + j
                            }
                        )
                        points.append(point)
                    except Exception as e:
                        print(f"❌ Error processing chunk {i + j}: {e}")
                        # Continue with other chunks
                        continue
            
            print(f"✅ Generated {len(points)} embeddings")
            
        except Exception as e:
            print(f"❌ Embedding generation error: {e}")
            raise HTTPException(status_code=500, detail=f"Embedding generation error: {str(e)}")
        
        # Upsert points to vector database
        print("💾 Storing in vector database...")
        try:
            if points:
                qdrant_client.upsert(
                    collection_name=collection_name,
                    points=points
                )
                print(f"✅ Stored {len(points)} vectors")
            else:
                raise HTTPException(status_code=500, detail="No valid embeddings generated")
                
        except Exception as e:
            print(f"❌ Vector database error: {e}")
            raise HTTPException(status_code=500, detail=f"Vector database error: {str(e)}")
        
        # Store document info
        documents[file.filename] = {
            "total_chunks": len(chunks),
            "stored_chunks": len(points),
            "validation": validation
        }
        
        print(f"🎉 Successfully processed {file.filename}")
        
        return {
            "success": True,
            "document_id": file.filename,
            "filename": file.filename,
            "total_chunks": len(chunks),
            "chunks_added": len(points),
            "text_preview": text[:200] + "..." if len(text) > 200 else text,
            "message": f"Successfully processed {file.filename} with {len(points)} chunks"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in PDF upload: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
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