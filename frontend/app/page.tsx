"use client";
import React, { useState, useRef } from "react";
import ReactMarkdown from 'react-markdown';
import styles from "./page.module.css";
import Image from "next/image";

interface Message {
  sender: "user" | "ai";
  content: string;
  isRag?: boolean;
  sources?: Array<{filename: string, chunk_index: number, score: number}>;
}

interface UploadedDocument {
  filename: string;
  chunks_added: number;
  text_preview: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDocument[]>([]);
  const [ragMode, setRagMode] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom when new message arrives
  React.useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load RAG stats on component mount
  React.useEffect(() => {
    loadRagStats();
  }, []);

  const loadRagStats = async () => {
    try {
      const response = await fetch("/api/rag-stats");
      if (response.ok) {
        const stats = await response.json();
        if (stats.documents > 0) {
          setRagMode(true);
          // Create dummy uploaded docs list from stats
          const docList = stats.document_list.map((filename: string) => ({
            filename,
            chunks_added: Math.ceil(stats.total_vectors / stats.documents),
            text_preview: "Previously uploaded document"
          }));
          setUploadedDocs(docList);
        }
      }
    } catch (err) {
      console.log("No existing RAG data");
    }
  };

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('/api/upload-pdf', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        // Try to parse as JSON first, fallback to text for HTML error pages
        let errorMessage = 'Upload failed';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.error || 'Upload failed';
        } catch (jsonError) {
          // If JSON parsing fails, try to extract meaningful error from text/HTML
          try {
            const errorText = await response.text();
            if (response.status === 413 || errorText.includes('Request Entity Too Large') || errorText.includes('size')) {
              errorMessage = 'File size exceeds 5MB limit. Please choose a smaller file.';
            } else if (response.status === 400) {
              errorMessage = 'Invalid file format. Please upload a PDF file.';
            } else {
              errorMessage = `Upload failed (${response.status})`;
            }
          } catch (textError) {
            errorMessage = `Upload failed (${response.status})`;
          }
        }
        throw new Error(errorMessage);
      }
      
      const result = await response.json();
      
      if (result.success) {
        const newDoc: UploadedDocument = {
          filename: result.filename,
          chunks_added: result.chunks_added,
          text_preview: result.text_preview
        };
        
        // Check if document was already processed
        const isAlreadyProcessed = result.chunks_added === "Already processed";
        
        if (!isAlreadyProcessed) {
          setUploadedDocs(prev => [...prev, newDoc]);
        }
        setRagMode(true);
        setShowUploadModal(false);
        
        // Add appropriate system message based on whether it was new or already processed
        const systemMessage = isAlreadyProcessed 
          ? `📋 **Document already processed!**\n\n**${result.filename}** was already in my knowledge base. No re-processing needed.\n\nYou can continue asking questions about this document!`
          : `✅ **PDF uploaded successfully!**\n\n**${result.filename}** has been processed and added to my knowledge base with ${result.chunks_added} text chunks.\n\nYou can now ask me questions about the content of this document!`;
        
        setMessages(prev => [...prev, {
          sender: "ai",
          content: systemMessage,
          isRag: true
        }]);
      } else {
        throw new Error(result.error || 'Upload failed');
      }
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim()) return;
    setError(null);
    const userMessage = input.trim();
    setMessages((prev) => [...prev, { sender: "user", content: userMessage }]);
    setInput("");
    setLoading(true);
    
    try {
      const endpoint = ragMode && uploadedDocs.length > 0 ? "/api/rag-chat" : "/api/chat";
      const requestBody = ragMode && uploadedDocs.length > 0 
        ? { user_message: userMessage, use_rag: true }
        : {
            developer_message: `You are Startup Mentor AI, an expert in startup best practices and entrepreneurship.

STRICT CONTENT BOUNDARIES:
- ONLY answer questions related to startups, entrepreneurship, business strategy, company building, and business operations
- If asked about programming, technology implementation, or other non-startup/business topics, politely redirect with: "I focus exclusively on startup and business advice. However, if you're building a tech startup, I can help with product strategy, team building, or finding technical talent. What startup or business challenges are you facing?"
- Always stay in character as a startup mentor
- Provide actionable, research-backed advice for entrepreneurs and business builders

FORMATTING GUIDELINES:
- Use simple text formulas instead of LaTeX (e.g., "CAC = Total Marketing Spend ÷ New Customers")
- Use markdown formatting for clarity
- Avoid complex mathematical notation

Give concise, well-formatted responses using markdown for better readability.`,
            user_message: userMessage,
          };

      // Send request to backend
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      
      if (!response.ok) {
        throw new Error("Server error: " + (await response.text()));
      }
      
      // Read streaming response
      const reader = response.body?.getReader();
      let aiMessage = "";
      let sources: any[] = [];
      let isRagResponse = false;
      let buffer = "";
      
      if (reader) {
        const decoder = new TextDecoder();
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value);
          buffer += chunk;
          
          if (ragMode && uploadedDocs.length > 0) {
            // Handle Server-Sent Events format for RAG
            const lines = buffer.split('\n');
            buffer = lines.pop() || ""; // Keep incomplete line in buffer
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const jsonStr = line.slice(6).trim(); // Remove 'data: '
                  if (jsonStr) {
                    const data = JSON.parse(jsonStr);
                    
                    if (data.type === "metadata") {
                      sources = data.sources || [];
                      isRagResponse = data.used_context;
                    } else if (data.type === "content") {
                      aiMessage += data.content;
                    } else if (data.type === "done") {
                      break;
                    } else if (data.error) {
                      throw new Error(data.error);
                    } else if (data.success === false) {
                      throw new Error(data.error || "Unknown error from backend");
                    }
                  }
                } catch (parseError) {
                  console.warn("Failed to parse SSE data:", line, parseError);
                }
              }
            }
          } else {
            // Regular streaming response for non-RAG mode
            aiMessage += chunk;
          }
          
          setMessages((prev) => {
            // If last message is AI, update it; else, add new
            if (prev[prev.length - 1]?.sender === "ai") {
              return [
                ...prev.slice(0, -1),
                { 
                  sender: "ai", 
                  content: aiMessage,
                  isRag: isRagResponse,
                  sources: sources
                },
              ];
            } else {
              return [...prev, { 
                sender: "ai", 
                content: aiMessage,
                isRag: isRagResponse,
                sources: sources
              }];
            }
          });
        }
      } else {
        // Fallback: not streaming
        const text = await response.text();
        setMessages((prev) => [...prev, { sender: "ai", content: text }]);
      }
    } catch (err: any) {
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const clearDocuments = async () => {
    try {
      const response = await fetch('/api/rag-clear', { method: 'DELETE' });
      if (response.ok) {
        setUploadedDocs([]);
        setRagMode(false);
        setMessages(prev => [...prev, {
          sender: "ai",
          content: "🗑️ All documents have been cleared from my knowledge base. I'm back to general startup mentoring mode.",
        }]);
      }
    } catch (err) {
      setError("Failed to clear documents");
    }
  };

  const openFileUpload = () => {
    setShowUploadModal(true);
  };

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div className={styles.heroImg}>
          <Image src="/ai_avatar.svg" alt="AI Avatar" width={48} height={48} />
        </div>
        <div className={styles.heroText}>
          Startup Mentor AI<br />
          <span style={{ fontWeight: 400, fontSize: "1rem" }}>
            {ragMode ? "Your document-enhanced startup advisor" : "Your friendly, research-backed startup advisor"}
          </span>
        </div>
        {uploadedDocs.length > 0 && (
          <div className={styles.docCount}>
            {uploadedDocs.length} doc{uploadedDocs.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>
      
      <main className={styles.main}>
        <h1 className={styles.title}>🚀 Startup Mentor AI</h1>
        <p className={styles.subtitle}>
          {ragMode 
            ? "Ask me about your uploaded startup documents or get general startup advice!" 
            : "Ask me anything about building a successful startup! Upload company documents for more specific insights."
          }
        </p>
        <div className={styles.limitNote}>
          📋 Upload limit: 5MB per file • Multiple files supported • Documents processed and indexed for search
        </div>
        
        {uploadedDocs.length > 0 && (
          <div className={styles.documentsPanel}>
            <div className={styles.documentsHeader}>
              <h3>📚 Uploaded Documents</h3>
              <button 
                className={styles.clearButton}
                onClick={clearDocuments}
                title="Clear all documents"
              >
                🗑️ Clear
              </button>
            </div>
            <div className={styles.documentsList}>
              {uploadedDocs.map((doc, idx) => (
                <div key={idx} className={styles.documentItem}>
                  <span className={styles.docName}>{doc.filename}</span>
                  <span className={styles.docInfo}>{doc.chunks_added} chunks</span>
                </div>
              ))}
            </div>
          </div>
        )}
        
        <div className={styles.chatContainer}>
          <div className={styles.chatHeader}>
            <div className={styles.chatTitle}>
              💬 {ragMode ? "Document-Enhanced Chat" : "Startup Advisory Chat"}
            </div>
            <button 
              className={styles.uploadButtonHeader}
              onClick={openFileUpload}
              disabled={uploading}
              title="Upload a startup or company document"
            >
              {uploading ? "⏳" : "📄"} Upload PDF
            </button>
          </div>
          
          <div className={styles.chatHistory}>
            {messages.length === 0 && (
              <div className={styles.placeholder}>
                <div className={styles.placeholderIcon}>💡</div>
                <div>
                  {ragMode 
                    ? "Ask questions about your uploaded documents or get general startup advice!" 
                    : "Start by asking a startup question or upload a company document for specific insights!"
                  }
                </div>
                {!ragMode && (
                  <div className={styles.placeholderHint}>
                    Try: "How do I validate my startup idea?" or upload a business plan for analysis
                  </div>
                )}
              </div>
            )}
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={
                  msg.sender === "user"
                    ? styles.userMessage
                    : styles.aiMessage
                }
              >
                {msg.sender === "user" ? (
                  <span className={styles.userAvatar} title="You">🧑</span>
                ) : (
                  <span className={styles.aiAvatar} title="Mentor AI">
                    <Image src="/ai_avatar.svg" alt="AI Avatar" width={24} height={24} />
                    {msg.isRag && <span className={styles.ragBadge} title="Answered using uploaded documents">📄</span>}
                  </span>
                )}
                <div className={styles.messageContent}>
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className={styles.sources}>
                      <strong>Sources:</strong>
                      {msg.sources.map((source, sidx) => (
                        <span key={sidx} className={styles.source}>
                          {source.filename} (chunk {source.chunk_index + 1}, relevance: {Math.round(source.score * 100)}%)
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>
          <form className={styles.inputForm} onSubmit={handleSend}>
            <input
              className={styles.inputBox}
              type="text"
              placeholder={ragMode ? "Ask about your documents or startup advice..." : "Ask your startup question..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              autoFocus
              aria-label="Ask your question"
            />
            <button
              className={styles.sendButton}
              type="submit"
              disabled={loading || !input.trim()}
            >
              {loading ? "..." : "Send"}
            </button>
          </form>
          {error && <div className={styles.error}>{error}</div>}
        </div>
      </main>
      
      {/* Upload Modal */}
      {showUploadModal && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h3>Upload Startup/Company Document</h3>
              <button 
                className={styles.closeButton}
                onClick={() => setShowUploadModal(false)}
              >
                ✕
              </button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.uploadInstructions}>
                <p><strong>📋 Supported document types:</strong></p>
                <ul>
                  <li>Business plans and pitch decks</li>
                  <li>Company documentation and reports</li>
                  <li>Startup case studies and research</li>
                  <li>Financial models and projections</li>
                  <li>Market research and analysis</li>
                </ul>
                <p><em>Please ensure your document contains startup or business-related content.</em></p>
                <p><strong>📊 Upload Limits:</strong> 5MB per file • Multiple files supported</p>
              </div>
              
              <div 
                className={styles.dropZone}
                onClick={() => fileInputRef.current?.click()}
                onDrop={(e) => {
                  e.preventDefault();
                  const file = e.dataTransfer.files[0];
                  if (file && file.type === 'application/pdf') {
                    handleFileUpload(file);
                  } else {
                    setError('Please upload a PDF file');
                  }
                }}
                onDragOver={(e) => e.preventDefault()}
              >
                <div className={styles.dropContent}>
                  📄
                  <p>Click to select or drag and drop a PDF file</p>
                  <small>Maximum: 5MB per file • Business/startup content only</small>
                </div>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    handleFileUpload(file);
                  }
                }}
              />
              {uploading && (
                <div className={styles.uploadProgress}>
                  Uploading and processing PDF... ⏳
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      <footer className={styles.footer}>
        <span>
          Built with ❤️ for founders. Powered by OpenAI, FastAPI & RAG.
        </span>
      </footer>
    </div>
  );
}
