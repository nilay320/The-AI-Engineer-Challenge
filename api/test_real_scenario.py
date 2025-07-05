#!/usr/bin/env python3
"""
Test script to simulate real PDF upload and chat scenario
"""
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from app import *
from openai import OpenAI

def test_real_scenario():
    print("🧪 Testing real PDF upload and chat scenario...")
    
    # Check API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set!")
        return False
    
    client = OpenAI(api_key=api_key)
    
    # Simulate a business document that should pass validation
    business_text = """
    Our startup company is developing an innovative business model to serve entrepreneurs in the market. 
    We are seeking funding from investors to scale our operations and grow our customer base. 
    Our business plan includes detailed financial projections, marketing strategy, and revenue forecasts.
    The company's vision is to become a leading provider of services to other startups and businesses.
    Our team includes experienced founders and a strong CEO who understands the venture capital landscape.
    We have identified significant market opportunities and developed a comprehensive strategy to capture them.
    Our product addresses key pain points for customers and provides substantial value to the business community.
    The investment will help us expand our operations, hire additional team members, and accelerate growth.
    """
    
    print("\n1. Testing content validation with business text...")
    validation = validate_content(business_text)
    print(f"   - Is valid: {validation['is_valid']}")
    print(f"   - Keyword count: {validation['keyword_count']}")
    print(f"   - Reason: {validation['reason']}")
    
    if not validation['is_valid']:
        print("❌ Business text failed validation!")
        return False
    
    print("\n2. Simulating PDF upload process...")
    
    # Clear any existing data
    try:
        qdrant_client.delete_collection(collection_name)
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        documents.clear()
        print("   - Cleared existing data")
    except:
        pass
    
    # Chunk the text
    chunks = chunk_text(business_text)
    print(f"   - Created {len(chunks)} chunks")
    
    # Generate embeddings and add to database
    points = []
    for i, chunk in enumerate(chunks):
        try:
            embedding = get_embedding(chunk, client)
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "text": chunk,
                    "filename": "business_plan.pdf",
                    "chunk_index": i
                }
            )
            points.append(point)
        except Exception as e:
            print(f"   - Error creating embedding for chunk {i}: {e}")
    
    print(f"   - Created {len(points)} vector points")
    
    # Add to database
    try:
        qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )
        print("   - Added points to vector database")
    except Exception as e:
        print(f"   - Error adding to database: {e}")
        return False
    
    # Update documents tracking
    documents["business_plan.pdf"] = {
        "total_chunks": len(chunks),
        "stored_chunks": len(points),
        "validation": validation
    }
    
    # Check database state
    collection_info = qdrant_client.get_collection(collection_name)
    print(f"   - Database now has {collection_info.points_count} points")
    
    print("\n3. Testing various queries...")
    
    test_queries = [
        "What is our business model?",
        "How much funding do we need?",
        "Who is our target market?",
        "What is our growth strategy?",
        "Tell me about the team",
        "What are the financial projections?"
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        
        # Get relevant documents
        relevant_docs = query_documents(query, client, 3)
        print(f"   - Found {len(relevant_docs)} relevant documents")
        
        if relevant_docs:
            print(f"   - Best match score: {relevant_docs[0]['score']:.3f}")
            print(f"   - Best match text: {relevant_docs[0]['text'][:100]}...")
            
            # Test full RAG response
            context = "\n\n".join([doc["text"] for doc in relevant_docs])
            prompt = f"""You are a helpful startup mentor AI. Use the following context from uploaded business documents to answer the user's question.

Context:
{context}

Question: {query}

Answer:"""
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful startup mentor AI assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.7
                )
                
                answer = response.choices[0].message.content
                print(f"   - RAG Answer: {answer[:150]}...")
                
            except Exception as e:
                print(f"   - Error generating response: {e}")
        else:
            print("   - No relevant documents found")
    
    print("\n🎉 Real scenario test completed!")
    return True

if __name__ == "__main__":
    test_real_scenario() 