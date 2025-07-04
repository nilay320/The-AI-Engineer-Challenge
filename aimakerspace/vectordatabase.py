import json
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import uuid
from .openai_utils.embedding import EmbeddingModel


class VectorDatabase:
    """In-memory vector database for storing and retrieving text embeddings."""
    
    def __init__(self, embedding_model: EmbeddingModel = None):
        self.embedding_model = embedding_model or EmbeddingModel()
        self.vectors = {}  # {id: {"text": str, "embedding": List[float], "metadata": dict}}
        self.dimension = None
    
    def add_text(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Add a text with its embedding to the database."""
        text_id = str(uuid.uuid4())
        embedding = self.embedding_model.get_embedding(text)
        
        if not embedding:
            raise ValueError(f"Failed to generate embedding for text: {text[:100]}...")
        
        if self.dimension is None:
            self.dimension = len(embedding)
        elif len(embedding) != self.dimension:
            raise ValueError(f"Embedding dimension mismatch: expected {self.dimension}, got {len(embedding)}")
        
        self.vectors[text_id] = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {}
        }
        
        return text_id
    
    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]] = None) -> List[str]:
        """Add multiple texts with their embeddings to the database."""
        if metadatas is None:
            metadatas = [{}] * len(texts)
        elif len(metadatas) != len(texts):
            raise ValueError("Number of metadatas must match number of texts")
        
        # Generate embeddings in batch for efficiency
        embeddings = self.embedding_model.get_embeddings(texts)
        
        text_ids = []
        for i, (text, embedding, metadata) in enumerate(zip(texts, embeddings, metadatas)):
            if not embedding:
                print(f"Warning: Failed to generate embedding for text {i}, skipping...")
                continue
                
            text_id = str(uuid.uuid4())
            
            if self.dimension is None:
                self.dimension = len(embedding)
            elif len(embedding) != self.dimension:
                print(f"Warning: Embedding dimension mismatch for text {i}, skipping...")
                continue
            
            self.vectors[text_id] = {
                "text": text,
                "embedding": embedding,
                "metadata": metadata
            }
            text_ids.append(text_id)
        
        return text_ids
    
    def search(self, query: str, top_k: int = 5, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """Search for similar texts based on query."""
        if not self.vectors:
            return []
        
        # Get query embedding
        query_embedding = self.embedding_model.get_embedding(query)
        if not query_embedding:
            return []
        
        # Calculate similarities
        similarities = []
        for text_id, data in self.vectors.items():
            similarity = self.embedding_model.cosine_similarity(query_embedding, data["embedding"])
            if similarity >= score_threshold:
                similarities.append({
                    "id": text_id,
                    "text": data["text"],
                    "metadata": data["metadata"],
                    "score": similarity
                })
        
        # Sort by similarity score (descending)
        similarities.sort(key=lambda x: x["score"], reverse=True)
        
        return similarities[:top_k]
    
    def get_by_id(self, text_id: str) -> Optional[Dict[str, Any]]:
        """Get a text by its ID."""
        if text_id in self.vectors:
            data = self.vectors[text_id]
            return {
                "id": text_id,
                "text": data["text"],
                "metadata": data["metadata"]
            }
        return None
    
    def delete_by_id(self, text_id: str) -> bool:
        """Delete a text by its ID."""
        if text_id in self.vectors:
            del self.vectors[text_id]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all vectors from the database."""
        self.vectors = {}
        self.dimension = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return {
            "total_vectors": len(self.vectors),
            "dimension": self.dimension,
            "model": self.embedding_model.model_name
        }
    
    def save_to_file(self, filepath: str) -> None:
        """Save the vector database to a JSON file."""
        data = {
            "dimension": self.dimension,
            "model": self.embedding_model.model_name,
            "vectors": self.vectors
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, filepath: str) -> None:
        """Load the vector database from a JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.dimension = data.get("dimension")
        self.vectors = data.get("vectors", {})
        
        # Update embedding model if different
        if "model" in data and data["model"] != self.embedding_model.model_name:
            print(f"Warning: Loaded model '{data['model']}' differs from current model '{self.embedding_model.model_name}'")
    
    def similarity_search_with_score_threshold(self, query: str, score_threshold: float = 0.7, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search with a minimum similarity score threshold."""
        results = self.search(query, top_k=len(self.vectors))  # Get all results first
        filtered_results = [r for r in results if r["score"] >= score_threshold]
        return filtered_results[:top_k] 