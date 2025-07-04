import openai
from typing import List, Dict, Any, Generator
import json


class ChatOpenAI:
    """OpenAI chat model for generating responses."""
    
    def __init__(self, model_name: str = "gpt-4o-mini", api_key: str = None):
        self.model_name = model_name
        if api_key:
            openai.api_key = api_key
        self.client = openai.OpenAI()
    
    def generate_response(self, messages: List[Dict[str, str]], stream: bool = False) -> str:
        """Generate a chat response."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=stream
            )
            
            if stream:
                return response  # Return the generator for streaming
            else:
                return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I apologize, but I encountered an error while processing your request."
    
    def generate_response_with_context(self, query: str, context: str, system_prompt: str = None) -> str:
        """Generate a response using the provided context."""
        if not system_prompt:
            system_prompt = """You are a helpful assistant that answers questions based on the provided context. 
            Use the context to answer the user's question. If the context doesn't contain enough information 
            to fully answer the question, say so and provide what information you can from the context."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
        ]
        
        return self.generate_response(messages)
    
    def stream_response_with_context(self, query: str, context: str, system_prompt: str = None) -> Generator[str, None, None]:
        """Stream a response using the provided context."""
        if not system_prompt:
            system_prompt = """You are a helpful assistant that answers questions based on the provided context. 
            Use the context to answer the user's question. If the context doesn't contain enough information 
            to fully answer the question, say so and provide what information you can from the context."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            print(f"Error streaming response: {e}")
            yield "I apologize, but I encountered an error while processing your request." 