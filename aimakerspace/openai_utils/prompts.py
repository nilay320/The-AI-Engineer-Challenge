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

STARTUP_RAG_PROMPT_TEMPLATE = """You are a startup mentor AI assistant. You have access to context from uploaded documents that may contain relevant startup advice, case studies, or information.

Context from uploaded documents:
{context}

User Question: {question}

Instructions:
- Use the provided context from the documents to answer startup-related questions
- Combine the document context with your general startup knowledge when appropriate
- If the documents contain specific examples, data, or advice relevant to the question, highlight that information
- If the uploaded documents don't contain relevant information for the question, rely on your general startup knowledge
- Provide actionable, practical advice when possible
- Be encouraging but realistic in your responses

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
    """Specialized prompt for startup mentor RAG interactions."""
    
    def __init__(self, template: str = STARTUP_RAG_PROMPT_TEMPLATE):
        super().__init__(template, input_variables=["context", "question"])
    
    def create_startup_rag_messages(self, question: str, context: str) -> List[Dict[str, str]]:
        """Create messages for startup RAG chat with context."""
        formatted_prompt = self.format_prompt(question=question, context=context)
        return [
            {"role": "system", "content": "You are an expert startup mentor with access to relevant document context."},
            {"role": "user", "content": formatted_prompt}
        ] 