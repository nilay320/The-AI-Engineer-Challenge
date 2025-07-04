import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import tempfile
import json

# Add the parent directory to the path to import aimakerspace
sys.path.append(str(Path(__file__).parent.parent))

from aimakerspace import (
    TextFileLoader, 
    CharacterTextSplitter, 
    VectorDatabase, 
    EmbeddingModel
)
from aimakerspace.openai_utils.chatmodel import ChatOpenAI
from aimakerspace.openai_utils.prompts import StartupRAGChatPrompt


class RAGService:
    """Service for handling RAG operations with PDF documents."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        # Initialize components
        self.embedding_model = EmbeddingModel(api_key=self.api_key)
        self.vector_db = VectorDatabase(embedding_model=self.embedding_model)
        self.chat_model = ChatOpenAI(model_name="gpt-4o-mini", api_key=self.api_key)
        self.text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.prompt_template = StartupRAGChatPrompt()
        
        # Storage for document metadata
        self.document_store = {}
        self.storage_path = Path("api/rag_storage")
        self.storage_path.mkdir(exist_ok=True)
    
    def process_pdf(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Process a PDF file and add it to the vector database."""
        try:
            # Load text from PDF
            loader = TextFileLoader("")
            text = loader.load_from_bytes(file_bytes, filename)
            
            if not text.strip():
                raise ValueError("No text could be extracted from the PDF")
            
            # Split text into chunks
            chunks = self.text_splitter.split_text(text)
            
            if not chunks:
                raise ValueError("No chunks could be created from the text")
            
            # Create metadata for each chunk
            metadatas = []
            for i, chunk in enumerate(chunks):
                metadatas.append({
                    "filename": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk)
                })
            
            # Add chunks to vector database
            chunk_ids = self.vector_db.add_texts(chunks, metadatas)
            
            # Store document metadata
            doc_id = filename  # Use filename as doc ID for simplicity
            self.document_store[doc_id] = {
                "filename": filename,
                "total_text_length": len(text),
                "total_chunks": len(chunks),
                "chunk_ids": chunk_ids,
                "processed_at": str(Path().cwd())
            }
            
            # Save the vector database state
            self._save_database()
            
            return {
                "success": True,
                "document_id": doc_id,
                "filename": filename,
                "total_chunks": len(chunks),
                "chunks_added": len(chunk_ids),
                "text_preview": text[:500] + "..." if len(text) > 500 else text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def query_documents(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Query the vector database and return relevant context."""
        try:
            if not self.vector_db.vectors:
                return {
                    "success": False,
                    "error": "No documents have been uploaded yet. Please upload a PDF first."
                }
            
            # Search for relevant chunks
            search_results = self.vector_db.search(query, top_k=top_k, score_threshold=0.1)
            
            if not search_results:
                return {
                    "success": True,
                    "context": "",
                    "message": "No relevant information found in the uploaded documents for your query.",
                    "sources": []
                }
            
            # Combine the context from relevant chunks
            context_parts = []
            sources = []
            
            for result in search_results:
                context_parts.append(result["text"])
                source_info = {
                    "filename": result["metadata"].get("filename", "Unknown"),
                    "chunk_index": result["metadata"].get("chunk_index", 0),
                    "score": round(result["score"], 3)
                }
                sources.append(source_info)
            
            context = "\n\n".join(context_parts)
            
            return {
                "success": True,
                "context": context,
                "sources": sources,
                "total_results": len(search_results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error querying documents: {str(e)}"
            }
    
    def generate_rag_response(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Generate a response using RAG with the uploaded documents."""
        try:
            # Get relevant context
            context_result = self.query_documents(query, top_k)
            
            if not context_result["success"]:
                return context_result
            
            context = context_result["context"]
            
            # If no context found, provide a helpful message
            if not context:
                return {
                    "success": True,
                    "response": "I don't have any relevant information in the uploaded documents to answer your question. Please try asking something related to the content of your uploaded PDF, or upload a relevant document first.",
                    "sources": [],
                    "used_context": False
                }
            
            # Generate response using the prompt template
            messages = self.prompt_template.create_startup_rag_messages(query, context)
            response = self.chat_model.generate_response(messages)
            
            return {
                "success": True,
                "response": response,
                "sources": context_result["sources"],
                "used_context": True,
                "context_length": len(context)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error generating response: {str(e)}"
            }
    
    def stream_rag_response(self, query: str, top_k: int = 5):
        """Stream a response using RAG with the uploaded documents."""
        try:
            # Get relevant context
            context_result = self.query_documents(query, top_k)
            
            if not context_result["success"]:
                yield f"data: {json.dumps(context_result)}\n\n"
                return
            
            context = context_result["context"]
            
            # If no context found, provide a helpful message
            if not context:
                no_context_response = {
                    "success": True,
                    "response": "I don't have any relevant information in the uploaded documents to answer your question. Please try asking something related to the content of your uploaded PDF, or upload a relevant document first.",
                    "sources": [],
                    "used_context": False
                }
                yield f"data: {json.dumps(no_context_response)}\n\n"
                return
            
            # Send metadata first
            metadata = {
                "type": "metadata",
                "sources": context_result["sources"],
                "used_context": True,
                "context_length": len(context)
            }
            yield f"data: {json.dumps(metadata)}\n\n"
            
            # Stream the response
            messages = self.prompt_template.create_startup_rag_messages(query, context)
            
            for chunk in self.chat_model.stream_response_with_context(query, context):
                chunk_data = {
                    "type": "content",
                    "content": chunk
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
            
            # Send final message
            final_data = {"type": "done"}
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            error_data = {
                "success": False,
                "error": f"Error streaming response: {str(e)}"
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the current vector database."""
        stats = self.vector_db.get_stats()
        stats["documents"] = len(self.document_store)
        stats["document_list"] = list(self.document_store.keys())
        return stats
    
    def clear_database(self) -> Dict[str, Any]:
        """Clear all documents from the vector database."""
        try:
            self.vector_db.clear()
            self.document_store = {}
            self._save_database()
            
            return {
                "success": True,
                "message": "All documents have been cleared from the database."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error clearing database: {str(e)}"
            }
    
    def _save_database(self):
        """Save the current state of the vector database."""
        try:
            # Save vector database
            db_path = self.storage_path / "vector_db.json"
            self.vector_db.save_to_file(str(db_path))
            
            # Save document metadata
            metadata_path = self.storage_path / "document_metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.document_store, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving database: {e}")
    
    def _load_database(self):
        """Load the vector database state if it exists."""
        try:
            db_path = self.storage_path / "vector_db.json"
            metadata_path = self.storage_path / "document_metadata.json"
            
            if db_path.exists():
                self.vector_db.load_from_file(str(db_path))
            
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.document_store = json.load(f)
        except Exception as e:
            print(f"Error loading database: {e}")


# Global RAG service instance
rag_service = None

def get_rag_service() -> RAGService:
    """Get or create the global RAG service instance."""
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
        rag_service._load_database()  # Load existing data if any
    return rag_service 