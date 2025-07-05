# Import required FastAPI components for building the API
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
# Import Pydantic for data validation and settings management
from pydantic import BaseModel
# Import OpenAI client for interacting with OpenAI's API
from openai import OpenAI
import os
import gc
import uuid
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
        
        # Try to create collection, recreate if it exists with invalid data
        try:
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        except Exception as collection_error:
            print(f"Collection creation failed, recreating: {collection_error}")
            try:
                qdrant_client.delete_collection(collection_name)
            except:
                pass  # Collection might not exist
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        
        print("RAG initialized successfully")
    except Exception as e:
        print(f"RAG initialization error: {e}")

def cleanup_memory():
    """Force garbage collection to free memory."""
    gc.collect()
    print("🧹 Memory cleanup completed")

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
    """Extract text from PDF bytes with memory optimization."""
    try:
        print(f"🔍 Processing PDF of {len(file_bytes)} bytes")
        
        # Create PDF reader with memory optimization
        pdf_file = io.BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        print(f"📄 PDF has {len(pdf_reader.pages)} pages")
        
        # Limit pages to prevent memory issues (reduced from 20 to 10)
        max_pages = 10
        pages_to_process = min(len(pdf_reader.pages), max_pages)
        if len(pdf_reader.pages) > max_pages:
            print(f"⚠️ Limiting to first {max_pages} pages to prevent memory issues")
        
        # Use list for efficient string joining (reduces memory copies)
        text_parts = []
        for i in range(pages_to_process):
            try:
                page_text = pdf_reader.pages[i].extract_text()
                if page_text and page_text.strip():
                    # Limit page text length to prevent memory explosion
                    if len(page_text) > 10000:  # 10KB per page max
                        page_text = page_text[:10000] + "... [truncated]"
                    text_parts.append(page_text)
                print(f"✅ Processed page {i+1}/{pages_to_process}")
            except Exception as e:
                print(f"⚠️ Error extracting page {i+1}: {e}")
                continue
        
        # Join all parts efficiently
        text = "\n".join(text_parts)
        
        # Limit total text length to prevent memory issues
        max_text_length = 50000  # 50KB max total text
        if len(text) > max_text_length:
            text = text[:max_text_length] + "\n... [Document truncated to prevent memory issues]"
            print(f"⚠️ Text truncated to {max_text_length} characters to prevent memory issues")
        
        print(f"✅ Extracted {len(text)} characters from {pages_to_process} pages")
        
        # Clear intermediate objects to free memory
        del text_parts
        del pdf_file
        del pdf_reader
        
        # Force garbage collection
        cleanup_memory()
        
        return text.strip()
        
    except Exception as e:
        print(f"❌ PDF extraction error: {e}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Split text into chunks with memory optimization."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    # Limit total chunks to prevent memory explosion
    max_chunks = 25
    
    while start < len(text) and len(chunks) < max_chunks:
        end = start + chunk_size
        if end > len(text):
            end = len(text)
        
        chunk = text[start:end]
        
        # Only add non-empty chunks
        if chunk.strip():
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    # If we hit the chunk limit, log it
    if len(chunks) >= max_chunks and start < len(text):
        print(f"⚠️ Chunk limit reached ({max_chunks}), remaining text truncated to prevent memory issues")
    
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
        print(f"🔍 Querying documents:")
        print(f"   - Query: {query}")
        print(f"   - Top K: {top_k}")
        
        if not qdrant_client:
            print("   - ❌ Qdrant client not initialized")
            return []
        
        # Check collection state
        try:
            collection_info = qdrant_client.get_collection(collection_name)
            print(f"   - Collection points: {collection_info.points_count}")
            if collection_info.points_count == 0:
                print("   - ❌ No documents in collection")
                return []
        except Exception as e:
            print(f"   - ❌ Collection error: {e}")
            return []
            
        query_embedding = get_embedding(query, client)
        print(f"   - Generated query embedding: {len(query_embedding)} dimensions")
        
        search_results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=top_k
        )
        
        print(f"   - Search returned {len(search_results)} results")
        
        results = []
        for i, result in enumerate(search_results):
            print(f"   - Result {i+1}: score={result.score:.3f}, filename={result.payload.get('filename', 'unknown')}")
            results.append({
                "text": result.payload["text"],
                "filename": result.payload["filename"],
                "score": result.score,
                "chunk_index": result.payload["chunk_index"]
            })
        
        return results
        
    except Exception as e:
        print(f"❌ Query error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
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
                # Debug: Check database state
                print(f"🔍 RAG Chat Debug:")
                print(f"   - Query: {request.user_message}")
                print(f"   - Qdrant client initialized: {qdrant_client is not None}")
                
                if qdrant_client:
                    try:
                        collection_info = qdrant_client.get_collection(collection_name)
                        print(f"   - Collection points: {collection_info.points_count}")
                        print(f"   - Documents in memory: {len(documents)}")
                        print(f"   - Document names: {list(documents.keys())}")
                    except Exception as e:
                        print(f"   - Collection error: {e}")
                
                # Get relevant documents
                relevant_docs = query_documents(request.user_message, client, 5)
                print(f"   - Found {len(relevant_docs)} relevant documents")
                
                if not relevant_docs:
                    yield "I don't have any relevant documents to answer your question. This might be because the documents were uploaded in a different serverless function instance. In Vercel's serverless environment, uploaded documents don't persist between requests. Please try uploading your PDF again and then immediately asking your question."
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
        
        # Chunk text with memory optimization
        print("✂️ Chunking text...")
        try:
            chunks = chunk_text(text)
            print(f"✅ Created {len(chunks)} chunks")
            
            # Limit chunks to prevent memory issues (reduced from 50 to 25)
            if len(chunks) > 25:
                chunks = chunks[:25]
                print(f"⚠️ Limited to first 25 chunks to prevent memory issues")
                
        except Exception as e:
            print(f"❌ Text chunking error: {e}")
            raise HTTPException(status_code=500, detail=f"Text processing error: {str(e)}")
        
        # Process chunks in very small batches to avoid memory issues
        print("🧠 Generating embeddings...")
        points = []
        batch_size = 3  # Reduced from 10 to 3 chunks at a time
        
        try:
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                print(f"Processing batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")
                
                # Process each chunk in the batch
                batch_points = []
                for j, chunk in enumerate(batch_chunks):
                    try:
                        # Truncate chunk if too long for embedding API
                        if len(chunk) > 5000:  # Reduced from default to 5000 chars
                            chunk = chunk[:5000] + "... [truncated for memory optimization]"
                        
                        embedding = get_embedding(chunk, client)
                        point = PointStruct(
                            id=str(uuid.uuid4()),  # Generate proper UUID
                            vector=embedding,
                            payload={
                                "text": chunk,
                                "filename": file.filename,
                                "chunk_index": i + j
                            }
                        )
                        batch_points.append(point)
                    except Exception as e:
                        print(f"❌ Error processing chunk {i + j}: {e}")
                        # Continue with other chunks
                        continue
                
                # Add batch to main points list
                points.extend(batch_points)
                
                # Clear batch variables to free memory
                del batch_points
                del batch_chunks
                
                # Force garbage collection after each batch
                cleanup_memory()
                
                print(f"✅ Completed batch {i//batch_size + 1}, total points: {len(points)}")
            
            print(f"✅ Generated {len(points)} embeddings")
            
        except Exception as e:
            print(f"❌ Embedding generation error: {e}")
            raise HTTPException(status_code=500, detail=f"Embedding generation error: {str(e)}")
        
        # Upsert points to vector database in smaller batches
        print("💾 Storing in vector database...")
        try:
            if points:
                # Upload in smaller batches to prevent memory spikes
                upload_batch_size = 5
                for i in range(0, len(points), upload_batch_size):
                    batch_points = points[i:i + upload_batch_size]
                    qdrant_client.upsert(
                        collection_name=collection_name,
                        points=batch_points
                    )
                    print(f"✅ Uploaded batch {i//upload_batch_size + 1}/{(len(points) + upload_batch_size - 1)//upload_batch_size}")
                
                print(f"✅ Stored {len(points)} vectors in total")
            else:
                raise HTTPException(status_code=500, detail="No valid embeddings generated")
                
        except Exception as e:
            print(f"❌ Vector database error: {e}")
            raise HTTPException(status_code=500, detail=f"Vector database error: {str(e)}")
        
        # Store document info with UUID tracking
        chunk_uuids = [point.id for point in points]
        documents[file.filename] = {
            "total_chunks": len(chunks),
            "stored_chunks": len(points),
            "validation": validation,
            "chunk_uuids": chunk_uuids  # Track UUIDs for potential cleanup
        }
        
        print(f"🎉 Successfully processed {file.filename}")
        
        # Final memory cleanup
        cleanup_memory()
        
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
            
        # Delete and recreate collection to clear invalid UUIDs
        try:
            qdrant_client.delete_collection(collection_name)
        except Exception as e:
            print(f"Collection deletion warning: {e}")
            
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        documents.clear()
        return {"success": True, "message": "Database cleared successfully"}
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

# Debug endpoint to check RAG state
@app.get("/api/rag-debug")
async def rag_debug():
    """Debug endpoint to check RAG state."""
    try:
        debug_info = {
            "qdrant_initialized": qdrant_client is not None,
            "documents_in_memory": len(documents),
            "document_names": list(documents.keys()),
            "collection_points": 0,
            "collection_error": None
        }
        
        if qdrant_client:
            try:
                collection_info = qdrant_client.get_collection(collection_name)
                debug_info["collection_points"] = collection_info.points_count
            except Exception as e:
                debug_info["collection_error"] = str(e)
        
        return debug_info
    except Exception as e:
        return {"error": str(e)}

# Entry point for running the application directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 