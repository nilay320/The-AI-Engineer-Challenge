# Startup Mentor AI Backend with RAG

This is a FastAPI-based backend service that provides a streaming chat interface using OpenAI's API, enhanced with RAG (Retrieval Augmented Generation) capabilities for startup and company document analysis.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- An OpenAI API key

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the `api` directory with the following content:

```
OPENAI_API_KEY=your-openai-api-key-here
```

## Running the Server

1. Make sure you're in the `api` directory:
```bash
cd api
```

2. Activate the virtual environment:
```bash
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

3. Start the server:
```bash
python app.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### Chat Endpoints

#### Regular Chat
- **URL**: `/api/chat`
- **Method**: POST
- **Description**: Standard chat with startup mentoring
- **Request Body**:
```json
{
    "developer_message": "string",
    "user_message": "string",
    "model": "gpt-4o-mini"  // optional
}
```
- **Response**: Streaming text response

#### RAG-Enhanced Chat
- **URL**: `/api/rag-chat`
- **Method**: POST
- **Description**: Chat with uploaded document context
- **Request Body**:
```json
{
    "user_message": "string",
    "use_rag": true
}
```
- **Response**: Streaming text response with document sources

### Document Management

#### Upload PDF
- **URL**: `/api/upload-pdf`
- **Method**: POST
- **Description**: Upload and process startup/company documents
- **Content-Type**: `multipart/form-data`
- **File Requirements**: 
  - PDF format only
  - Max size: 10MB
  - Must contain startup/business-related content
- **Response**: Processing results with validation

#### Get Database Stats
- **URL**: `/api/rag-stats`
- **Method**: GET
- **Description**: Get statistics about uploaded documents
- **Response**: Document count, vector database info

#### Clear Database
- **URL**: `/api/rag-clear`
- **Method**: DELETE
- **Description**: Remove all uploaded documents
- **Response**: Confirmation message

#### Query Documents
- **URL**: `/api/query-documents`
- **Method**: POST
- **Description**: Test document retrieval
- **Request Body**:
```json
{
    "query": "string",
    "top_k": 5  // optional
}
```
- **Response**: Relevant document chunks

### Utility Endpoints

#### Health Check
- **URL**: `/api/health`
- **Method**: GET
- **Response**: `{"status": "ok"}`

## Features

### RAG (Retrieval Augmented Generation)
- **Document Processing**: Extracts text from PDFs and creates searchable embeddings
- **Content Validation**: Ensures uploaded documents are startup/business-related
- **Intelligent Retrieval**: Finds relevant document sections for user queries
- **Source Attribution**: Provides references to specific document chunks
- **Persistent Storage**: Maintains document database across sessions

### Content Filtering
- **Startup Focus**: Only accepts business and startup-related documents
- **AI Validation**: Uses OpenAI to assess document relevance
- **Keyword Analysis**: Checks for business terminology
- **Quality Scoring**: Provides content relevance scores

### Startup Mentoring
- **Specialized Prompts**: Focused on entrepreneurship and business advice
- **Document Integration**: Combines uploaded content with general startup knowledge
- **Boundary Enforcement**: Redirects non-business questions appropriately

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## CORS Configuration

The API is configured to accept requests from any origin (`*`). This can be modified in the `app.py` file if you need to restrict access to specific domains.

## Error Handling

The API includes comprehensive error handling for:
- Invalid API keys
- OpenAI API errors
- PDF processing errors
- Document validation failures
- Vector database errors
- General server errors

All errors return appropriate HTTP status codes with descriptive error messages.

## File Structure

```
api/
├── app.py                 # Main FastAPI application
├── rag_service.py        # RAG functionality and document processing
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this)
├── .venv/               # Virtual environment
└── rag_storage/         # Document database storage (auto-created)
    ├── vector_db.json   # Vector embeddings
    └── document_metadata.json  # Document information
```

## Dependencies

Key dependencies include:
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `openai`: OpenAI API client
- `PyPDF2`: PDF text extraction
- `numpy`: Vector operations
- `pydantic`: Data validation

## Development Notes

- The system uses OpenAI's `text-embedding-3-small` model for embeddings
- Chat responses use `gpt-4o-mini` model
- Vector similarity search uses cosine similarity
- Document chunks are created with 1000 character limit and 200 character overlap
- Content validation requires a minimum relevance score of 4.0/10 