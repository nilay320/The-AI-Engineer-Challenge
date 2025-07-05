#!/usr/bin/env python3
"""
Test script to debug RAG functionality locally
"""
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from app import *
from openai import OpenAI

def test_rag_step_by_step():
    print("🧪 Testing RAG functionality step by step...")
    
    # Test 1: Check if OpenAI API key is set
    print("\n1. Testing OpenAI API key...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set!")
        print("Please set it with: export OPENAI_API_KEY=your_key_here")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
    except Exception as e:
        print(f"❌ OpenAI client error: {e}")
        return False
    
    # Test 2: Check RAG initialization
    print("\n2. Testing RAG initialization...")
    print(f"   - Qdrant client: {qdrant_client is not None}")
    print(f"   - Collection name: {collection_name}")
    print(f"   - Documents in memory: {len(documents)}")
    
    if qdrant_client:
        try:
            collection_info = qdrant_client.get_collection(collection_name)
            print(f"   - Collection points: {collection_info.points_count}")
        except Exception as e:
            print(f"   - Collection error: {e}")
    
    # Test 3: Test embedding generation
    print("\n3. Testing embedding generation...")
    test_text = "This is a test business document about startups and companies."
    try:
        embedding = get_embedding(test_text, client)
        print(f"   - Embedding dimensions: {len(embedding)}")
        print(f"   - First 5 values: {embedding[:5]}")
        print("✅ Embedding generation works")
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        return False
    
    # Test 4: Test content validation
    print("\n4. Testing content validation...")
    try:
        validation = validate_content(test_text)
        print(f"   - Is valid: {validation['is_valid']}")
        print(f"   - Keyword count: {validation['keyword_count']}")
        print(f"   - Reason: {validation['reason']}")
        print("✅ Content validation works")
    except Exception as e:
        print(f"❌ Content validation failed: {e}")
        return False
    
    # Test 5: Test text chunking
    print("\n5. Testing text chunking...")
    try:
        chunks = chunk_text(test_text)
        print(f"   - Number of chunks: {len(chunks)}")
        print(f"   - First chunk: {chunks[0][:50]}...")
        print("✅ Text chunking works")
    except Exception as e:
        print(f"❌ Text chunking failed: {e}")
        return False
    
    # Test 6: Test adding documents to vector database
    print("\n6. Testing vector database operations...")
    try:
        # Create a test point
        test_embedding = get_embedding("Test business content", client)
        test_point = PointStruct(
            id=str(uuid.uuid4()),
            vector=test_embedding,
            payload={
                "text": "Test business content about startups",
                "filename": "test.pdf",
                "chunk_index": 0
            }
        )
        
        # Add to database
        qdrant_client.upsert(
            collection_name=collection_name,
            points=[test_point]
        )
        
        # Check if it was added
        collection_info = qdrant_client.get_collection(collection_name)
        print(f"   - Points after adding test: {collection_info.points_count}")
        print("✅ Vector database operations work")
        
    except Exception as e:
        print(f"❌ Vector database operations failed: {e}")
        return False
    
    # Test 7: Test querying
    print("\n7. Testing document querying...")
    try:
        results = query_documents("business startup", client, 5)
        print(f"   - Query results: {len(results)}")
        if results:
            print(f"   - First result score: {results[0]['score']}")
            print(f"   - First result text: {results[0]['text'][:50]}...")
        print("✅ Document querying works")
    except Exception as e:
        print(f"❌ Document querying failed: {e}")
        return False
    
    print("\n🎉 All tests passed! RAG functionality is working.")
    return True

if __name__ == "__main__":
    test_rag_step_by_step() 