"""
Simple RAG implementation for Vercel deployment
Uses only standard dependencies without complex imports
"""

import os
import PyPDF2
import io
from typing import List, Dict, Any
from openai import OpenAI
import json
import re
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import numpy as np


class SimpleRAGService:
    """Simple RAG service that works with Vercel serverless functions."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        
        # Initialize Qdrant in-memory
        self.qdrant_client = QdrantClient(":memory:")
        self.collection_name = "startup_docs"
        self.vector_size = 1536  # OpenAI text-embedding-3-small dimension
        
        # Initialize collection
        self._init_collection()
        
        # Document storage
        self.documents = {}
    
    def _init_collection(self):
        """Initialize Qdrant collection."""
        try:
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )
        except Exception as e:
            # Collection might already exist
            pass
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI."""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return [0.0] * self.vector_size
    
    def _extract_text_from_pdf(self, file_bytes: bytes) -> str:
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
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
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
            
            # Move start position with overlap
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _validate_content(self, text: str) -> Dict[str, Any]:
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
        
        # Simple validation: at least 3 business keywords
        is_valid = keyword_count >= 3
        
        return {
            "is_valid": is_valid,
            "keyword_count": keyword_count,
            "reason": f"Found {keyword_count} business keywords"
        }
    
    def process_pdf(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Process PDF and add to vector database."""
        try:
            # Extract text
            text = self._extract_text_from_pdf(file_bytes)
            if not text:
                return {"success": False, "error": "Could not extract text from PDF"}
            
            # Validate content
            validation = self._validate_content(text)
            if not validation["is_valid"]:
                return {
                    "success": False, 
                    "error": f"Document doesn't contain enough business content. {validation['reason']}"
                }
            
            # Chunk text
            chunks = self._chunk_text(text)
            
            # Add chunks to vector database
            points = []
            for i, chunk in enumerate(chunks):
                embedding = self._get_embedding(chunk)
                point = PointStruct(
                    id=f"{filename}_{i}",
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "filename": filename,
                        "chunk_index": i
                    }
                )
                points.append(point)
            
            # Upsert points
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            # Store document info
            self.documents[filename] = {
                "total_chunks": len(chunks),
                "validation": validation
            }
            
            return {
                "success": True,
                "document_id": filename,
                "filename": filename,
                "total_chunks": len(chunks),
                "chunks_added": len(chunks),
                "text_preview": text[:200] + "..." if len(text) > 200 else text,
                "message": f"Successfully processed {filename} with {len(chunks)} chunks"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Processing error: {str(e)}"}
    
    def query_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query documents for relevant chunks."""
        try:
            query_embedding = self._get_embedding(query)
            
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
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
    
    def generate_rag_response(self, query: str, top_k: int = 5) -> str:
        """Generate RAG response."""
        try:
            # Get relevant documents
            relevant_docs = self.query_documents(query, top_k)
            
            if not relevant_docs:
                return "I don't have any relevant documents to answer your question."
            
            # Create context from relevant documents
            context = "\n\n".join([doc["text"] for doc in relevant_docs])
            
            # Create prompt
            prompt = f"""You are a helpful startup mentor AI. Use the following context from uploaded business documents to answer the user's question. If the context doesn't contain relevant information, say so.

Context:
{context}

Question: {query}

Answer:"""
            
            # Generate response
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful startup mentor AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def stream_rag_response(self, query: str, top_k: int = 5):
        """Stream RAG response."""
        try:
            # Get relevant documents
            relevant_docs = self.query_documents(query, top_k)
            
            if not relevant_docs:
                yield "I don't have any relevant documents to answer your question."
                return
            
            # Create context
            context = "\n\n".join([doc["text"] for doc in relevant_docs])
            
            # Create prompt
            prompt = f"""You are a helpful startup mentor AI. Use the following context from uploaded business documents to answer the user's question.

Context:
{context}

Question: {query}

Answer:"""
            
            # Stream response
            stream = self.client.chat.completions.create(
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
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return {
                "total_documents": len(self.documents),
                "total_chunks": collection_info.points_count,
                "documents": list(self.documents.keys())
            }
        except Exception as e:
            return {"error": str(e)}
    
    def clear_database(self) -> Dict[str, Any]:
        """Clear all documents."""
        try:
            self.qdrant_client.delete_collection(self.collection_name)
            self._init_collection()
            self.documents = {}
            return {"success": True, "message": "Database cleared"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global instance
_simple_rag_service = None

def get_simple_rag_service() -> SimpleRAGService:
    """Get or create simple RAG service instance."""
    global _simple_rag_service
    if _simple_rag_service is None:
        _simple_rag_service = SimpleRAGService()
    return _simple_rag_service 