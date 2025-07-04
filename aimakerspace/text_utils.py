import io
from typing import List, Optional
import PyPDF2
from pathlib import Path


class TextFileLoader:
    """Load and process text files including PDFs."""
    
    def __init__(self, path: str):
        self.path = path
    
    def load(self) -> str:
        """Load text from file path."""
        path = Path(self.path)
        
        if path.suffix.lower() == '.pdf':
            return self._load_pdf()
        else:
            with open(self.path, 'r', encoding='utf-8') as file:
                return file.read()
    
    def load_from_bytes(self, file_bytes: bytes, filename: str) -> str:
        """Load text from file bytes."""
        if filename.lower().endswith('.pdf'):
            return self._load_pdf_from_bytes(file_bytes)
        else:
            return file_bytes.decode('utf-8')
    
    def _load_pdf(self) -> str:
        """Load text from PDF file."""
        with open(self.path, 'rb') as file:
            return self._extract_pdf_text(file)
    
    def _load_pdf_from_bytes(self, file_bytes: bytes) -> str:
        """Load text from PDF bytes."""
        pdf_file = io.BytesIO(file_bytes)
        return self._extract_pdf_text(pdf_file)
    
    def _extract_pdf_text(self, file_obj) -> str:
        """Extract text from PDF file object."""
        pdf_reader = PyPDF2.PdfReader(file_obj)
        text = ""
        
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()


class CharacterTextSplitter:
    """Split text into chunks by character count."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at a sentence or word boundary if possible
            if end < len(text):
                # Look for sentence endings first
                for i in range(end, max(start + self.chunk_size // 2, end - 100), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
                else:
                    # If no sentence ending found, look for word boundaries
                    for i in range(end, max(start + self.chunk_size // 2, end - 50), -1):
                        if text[i].isspace():
                            end = i
                            break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = max(start + 1, end - self.chunk_overlap)
            
            if start >= len(text):
                break
        
        return chunks 