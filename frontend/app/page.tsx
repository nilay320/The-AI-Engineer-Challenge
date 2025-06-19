"use client";
import React, { useState, useRef } from "react";
import styles from "./page.module.css";
import Image from "next/image";

interface Message {
  sender: "user" | "ai";
  content: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when new message arrives
  React.useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim()) return;
    setError(null);
    const userMessage = input.trim();
    setMessages((prev) => [...prev, { sender: "user", content: userMessage }]);
    setInput("");
    setLoading(true);
    try {
      // Send request to backend
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          developer_message: "You are Startup Mentor AI, an expert in startup best practices. Give actionable, research-backed advice.",
          user_message: userMessage,
        }),
      });
      if (!response.ok) {
        throw new Error("Server error: " + (await response.text()));
      }
      // Read streaming response
      const reader = response.body?.getReader();
      let aiMessage = "";
      if (reader) {
        const decoder = new TextDecoder();
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          aiMessage += decoder.decode(value);
          setMessages((prev) => {
            // If last message is AI, update it; else, add new
            if (prev[prev.length - 1]?.sender === "ai") {
              return [
                ...prev.slice(0, -1),
                { sender: "ai", content: aiMessage },
              ];
            } else {
              return [...prev, { sender: "ai", content: aiMessage }];
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

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div className={styles.heroImg}>
          <Image src="/ai_avatar.svg" alt="AI Avatar" width={48} height={48} />
        </div>
        <div className={styles.heroText}>
          Startup Mentor AI<br />
          <span style={{ fontWeight: 400, fontSize: "1rem" }}>
            Your friendly, research-backed startup advisor
          </span>
        </div>
      </div>
      <main className={styles.main}>
        <h1 className={styles.title}>🚀 Startup Mentor AI</h1>
        <p className={styles.subtitle}>
          Ask me anything about building a successful startup! I'll give you research-backed, actionable advice.
        </p>
        <div className={styles.chatContainer}>
          <div className={styles.chatHistory}>
            {messages.length === 0 && (
              <div className={styles.placeholder}>Start the conversation! 👋</div>
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
                  </span>
                )}
                <span className={styles.messageContent}>{msg.content}</span>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>
          <form className={styles.inputForm} onSubmit={handleSend}>
            <input
              className={styles.inputBox}
              type="text"
              placeholder="Ask your startup question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              autoFocus
              aria-label="Ask your startup question"
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
      <footer className={styles.footer}>
        <span>
          Built with ❤️ for founders. Powered by OpenAI & FastAPI.
        </span>
      </footer>
    </div>
  );
}
