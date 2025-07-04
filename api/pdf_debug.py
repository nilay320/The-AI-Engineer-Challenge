#!/usr/bin/env python3
"""
PDF Debug Tool for RAG System
Helps diagnose why a specific PDF might be excluded from the RAG system.
"""

import sys
import os
from pathlib import Path
import PyPDF2
import io

# Add parent directory to path for aimakerspace imports
sys.path.append(str(Path(__file__).parent.parent))

from aimakerspace import TextFileLoader
from rag_service import RAGService

def analyze_pdf(pdf_path: str):
    """Analyze a PDF file and show why it might be excluded."""
    
    print(f"🔍 Analyzing PDF: {pdf_path}")
    print("=" * 60)
    
    # Check if file exists
    if not Path(pdf_path).exists():
        print("❌ ERROR: File does not exist!")
        return
    
    # Check file extension
    if not pdf_path.lower().endswith('.pdf'):
        print("❌ ERROR: File is not a PDF (must have .pdf extension)")
        return
    
    # Check file size
    file_size = Path(pdf_path).stat().st_size
    max_size = 10 * 1024 * 1024  # 10MB
    print(f"📁 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    if file_size > max_size:
        print("❌ ERROR: File exceeds 10MB limit!")
        return
    else:
        print("✅ File size OK")
    
    # Try to extract text
    print("\n📄 Text Extraction:")
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            print(f"📑 Number of pages: {len(pdf_reader.pages)}")
            
            text = ""
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                text += page_text + "\n"
                print(f"   Page {i+1}: {len(page_text)} characters extracted")
            
            if not text.strip():
                print("❌ ERROR: No text could be extracted from PDF!")
                print("   This might be an image-only PDF or corrupted file.")
                return
            else:
                print(f"✅ Total text extracted: {len(text)} characters")
                
        # Show text preview
        print(f"\n📝 Text Preview (first 500 chars):")
        print("-" * 40)
        print(text[:500])
        if len(text) > 500:
            print("...")
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ ERROR extracting text: {str(e)}")
        return
    
    # Analyze content validation
    print(f"\n🤖 Content Validation Analysis:")
    try:
        # Load with RAG service
        with open(pdf_path, 'rb') as file:
            file_bytes = file.read()
        
        rag_service = RAGService()
        filename = Path(pdf_path).name
        
        # Simulate the validation process
        validation_result = rag_service._validate_startup_content(text)
        
        print(f"🎯 Final Relevance Score: {validation_result['final_score']}/10")
        print(f"📊 Keyword Analysis:")
        print(f"   - Keywords found: {validation_result['keyword_count']}")
        print(f"   - Keyword density: {validation_result['keyword_density']}%")
        print(f"🤖 AI Assessment:")
        print(f"   - AI Score: {validation_result['ai_score']}/10")
        print(f"   - AI Reason: {validation_result['ai_reason']}")
        
        if validation_result['is_valid']:
            print("✅ RESULT: Document PASSES content validation!")
            print("   This PDF should be accepted by the RAG system.")
        else:
            print("❌ RESULT: Document FAILS content validation!")
            print(f"   Minimum required score: 4.0/10")
            print(f"   Your document scored: {validation_result['final_score']}/10")
            print("   This PDF will be EXCLUDED from the RAG system.")
            
        # Show validation details
        print(f"\n📋 Detailed Validation Info:")
        details = validation_result['validation_details']
        print(f"   - Total words analyzed: {details['total_words']}")
        print(f"   - Business keywords found: {details['keywords_found']}")
        print(f"   - {details['ai_assessment']}")
        
    except Exception as e:
        print(f"❌ ERROR in content validation: {str(e)}")
        return
    
    # Test full processing
    print(f"\n🔄 Testing Full Processing:")
    try:
        result = rag_service.process_pdf(file_bytes, filename)
        
        if result['success']:
            print("✅ SUCCESS: PDF would be fully processed and added to RAG!")
            print(f"   - Document ID: {result['document_id']}")
            print(f"   - Total chunks: {result['total_chunks']}")
            print(f"   - Chunks added: {result['chunks_added']}")
        else:
            print("❌ FAILED: PDF processing failed!")
            print(f"   Error: {result['error']}")
            if 'validation_details' in result:
                print(f"   Validation details: {result['validation_details']}")
                
    except Exception as e:
        print(f"❌ ERROR in full processing: {str(e)}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python pdf_debug.py <path_to_pdf>")
        print("Example: python pdf_debug.py ../docs/business_plan.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    analyze_pdf(pdf_path)

if __name__ == "__main__":
    main() 