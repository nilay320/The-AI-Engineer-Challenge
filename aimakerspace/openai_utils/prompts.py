from typing import Dict, Any, List


class ChatPrompt:
    """Template for chat prompts with variable substitution."""
    
    def __init__(self, template: str, input_variables: List[str] = None):
        self.template = template
        self.input_variables = input_variables or []
    
    def format_prompt(self, **kwargs) -> str:
        """Format the prompt template with provided variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required variable: {e}")
    
    def create_messages(self, role: str = "user", **kwargs) -> List[Dict[str, str]]:
        """Create chat messages from the formatted prompt."""
        formatted_prompt = self.format_prompt(**kwargs)
        return [{"role": role, "content": formatted_prompt}]


# Pre-defined prompt templates for RAG
RAG_PROMPT_TEMPLATE = """You are a helpful assistant that answers questions based on the provided context from documents.

Context from documents:
{context}

User Question: {question}

Instructions:
- Use the provided context to answer the user's question as accurately as possible
- If the context doesn't contain enough information to fully answer the question, acknowledge this and provide what information you can
- If the question cannot be answered from the context, politely say so and suggest what type of information would be needed
- Be concise but thorough in your response
- If you reference specific information from the context, you can mention that it comes from the uploaded document

Answer:"""

STARTUP_RAG_PROMPT_TEMPLATE = """You are a specialized startup mentor AI assistant. You ONLY provide advice on two types of questions:

1. GENERAL STARTUP QUESTIONS: About entrepreneurship, business strategy, company building, and startup best practices
2. DOCUMENT-SPECIFIC QUESTIONS: About the content in uploaded startup/company documents

STRICT CONTENT BOUNDARIES:
- ONLY answer questions related to startups, entrepreneurship, business operations, company analysis, or content from uploaded business documents
- If asked about non-startup topics (technology implementation, programming, personal advice, academic subjects, etc.), respond with: "I specialize exclusively in startup and business advice. I can help with entrepreneurial questions or analyze your uploaded business documents. What startup or company challenge can I help you with?"

Context from uploaded business documents:
{context}

User Question: {question}

RESPONSE GUIDELINES:
- If the question is about uploaded documents: Use the provided context to give specific insights about the documents
- If the question is a general startup question: Provide expert startup advice even if no relevant document context exists
- Combine document insights with general startup knowledge when appropriate
- Be actionable, practical, and encouraging but realistic
- If document context exists but isn't relevant to the question, focus on general startup advice
- Always stay focused on business and entrepreneurial topics

Response:"""


class RAGChatPrompt(ChatPrompt):
    """Specialized prompt for RAG (Retrieval Augmented Generation) interactions."""
    
    def __init__(self, template: str = RAG_PROMPT_TEMPLATE):
        super().__init__(template, input_variables=["context", "question"])
    
    def create_rag_messages(self, question: str, context: str, system_role: str = "assistant") -> List[Dict[str, str]]:
        """Create messages for RAG chat with context."""
        formatted_prompt = self.format_prompt(question=question, context=context)
        return [
            {"role": "system", "content": "You are a helpful assistant that uses provided document context to answer questions."},
            {"role": "user", "content": formatted_prompt}
        ]


class StartupRAGChatPrompt(ChatPrompt):
    """Specialized prompt for startup mentor RAG interactions with strict content boundaries."""
    
    def __init__(self, template: str = STARTUP_RAG_PROMPT_TEMPLATE):
        super().__init__(template, input_variables=["context", "question"])
    
    def create_startup_rag_messages(self, question: str, context: str) -> List[Dict[str, str]]:
        """Create messages for startup RAG chat with context."""
        formatted_prompt = self.format_prompt(question=question, context=context)
        return [
            {"role": "system", "content": "You are a specialized startup mentor AI that only discusses entrepreneurship, business strategy, and uploaded business documents. Redirect all non-startup questions politely."},
            {"role": "user", "content": formatted_prompt}
        ] 