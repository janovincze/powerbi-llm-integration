/**
 * Chat Interface Component
 *
 * Provides the main chat UI for interacting with the LLM.
 * Displays message history and input field.
 */

import * as React from "react";
import { useState, useRef, useEffect, useCallback } from "react";
import { ChatMessage } from "../types";

interface ChatInterfaceProps {
    messages: ChatMessage[];
    isLoading: boolean;
    onSendMessage: (message: string) => void;
    fontSize: number;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
    messages,
    isLoading,
    onSendMessage,
    fontSize,
}) => {
    const [input, setInput] = useState("");
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    // Focus input on mount
    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    /**
     * Handle sending message
     */
    const handleSend = useCallback(() => {
        if (input.trim() && !isLoading) {
            onSendMessage(input.trim());
            setInput("");
        }
    }, [input, isLoading, onSendMessage]);

    /**
     * Handle keyboard events
     */
    const handleKeyDown = useCallback(
        (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
            }
        },
        [handleSend]
    );

    /**
     * Auto-resize textarea
     */
    const handleInputChange = useCallback(
        (e: React.ChangeEvent<HTMLTextAreaElement>) => {
            setInput(e.target.value);

            // Auto-resize
            const textarea = e.target;
            textarea.style.height = "auto";
            textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
        },
        []
    );

    /**
     * Format message content with markdown-like styling
     */
    const formatContent = (content: string): React.ReactNode => {
        // Split by code blocks
        const parts = content.split(/(```[\s\S]*?```)/g);

        return parts.map((part, index) => {
            if (part.startsWith("```")) {
                // Code block
                const match = part.match(/```(\w+)?\n?([\s\S]*?)```/);
                if (match) {
                    const language = match[1] || "";
                    const code = match[2].trim();
                    return (
                        <pre key={index} className="chat-code-block">
                            <code className={`language-${language}`}>{code}</code>
                        </pre>
                    );
                }
            }

            // Process inline formatting
            return (
                <span key={index}>
                    {part.split("\n").map((line, lineIndex) => {
                        // Bold
                        let formattedLine: React.ReactNode = line.replace(
                            /\*\*(.*?)\*\*/g,
                            "<strong>$1</strong>"
                        );

                        // Inline code
                        formattedLine = line.replace(
                            /`([^`]+)`/g,
                            '<code class="inline-code">$1</code>'
                        );

                        // Bullet points
                        if (line.trim().startsWith("•") || line.trim().startsWith("-")) {
                            return (
                                <div key={lineIndex} className="chat-bullet">
                                    <span
                                        dangerouslySetInnerHTML={{
                                            __html: formattedLine as string,
                                        }}
                                    />
                                </div>
                            );
                        }

                        return (
                            <React.Fragment key={lineIndex}>
                                <span
                                    dangerouslySetInnerHTML={{
                                        __html: formattedLine as string,
                                    }}
                                />
                                {lineIndex < part.split("\n").length - 1 && <br />}
                            </React.Fragment>
                        );
                    })}
                </span>
            );
        });
    };

    /**
     * Get message style class based on role and type
     */
    const getMessageClass = (message: ChatMessage): string => {
        const classes = ["chat-message", `chat-message--${message.role}`];

        if (message.type === "error") {
            classes.push("chat-message--error");
        } else if (message.type === "dax" || message.type === "sql") {
            classes.push("chat-message--code");
        }

        return classes.join(" ");
    };

    return (
        <div className="chat-interface" style={{ fontSize: `${fontSize}px` }}>
            <div className="chat-messages">
                {messages.map((message) => (
                    <div key={message.id} className={getMessageClass(message)}>
                        <div className="chat-message__avatar">
                            {message.role === "user" ? "👤" : "🤖"}
                        </div>
                        <div className="chat-message__content">
                            {formatContent(message.content)}

                            {message.metadata?.sources &&
                                message.metadata.sources.length > 0 && (
                                    <div className="chat-message__sources">
                                        <span className="sources-label">Sources:</span>
                                        {message.metadata.sources.map((source, idx) => (
                                            <span key={idx} className="source-tag">
                                                {source}
                                            </span>
                                        ))}
                                    </div>
                                )}
                        </div>
                        <div className="chat-message__time">
                            {message.timestamp.toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                            })}
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div className="chat-message chat-message--assistant chat-message--loading">
                        <div className="chat-message__avatar">🤖</div>
                        <div className="chat-message__content">
                            <div className="loading-dots">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-area">
                <textarea
                    ref={inputRef}
                    value={input}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask about your data..."
                    rows={1}
                    disabled={isLoading}
                    className="chat-input"
                />
                <button
                    onClick={handleSend}
                    disabled={isLoading || !input.trim()}
                    className="chat-send-button"
                    title="Send message (Enter)"
                >
                    {isLoading ? "..." : "→"}
                </button>
            </div>
        </div>
    );
};
