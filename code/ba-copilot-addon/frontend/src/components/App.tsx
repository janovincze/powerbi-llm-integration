/**
 * App Component - Root React Component
 *
 * Main container for the BA Copilot visual that manages
 * layout, state, and child component rendering.
 */

import * as React from "react";
import { useState, useEffect, useCallback } from "react";
import { AppProps, ChatMessage, AppState } from "../types";
import { ChatInterface } from "./ChatInterface";
import { QuickActions } from "./QuickActions";
import { CodeDisplay } from "./CodeDisplay";
import { Header } from "./Header";
import { LandingPage } from "./LandingPage";
import { LLMService } from "../services/llmService";

const initialState: AppState = {
    messages: [],
    isLoading: false,
    error: null,
    isConnected: false,
    activeTab: "chat",
};

export const App: React.FC<AppProps> = ({
    width,
    height,
    settings,
    visualContext,
    host,
}) => {
    const [state, setState] = useState<AppState>(initialState);
    const [llmService, setLLMService] = useState<LLMService | null>(null);
    const [generatedCode, setGeneratedCode] = useState<{
        type: "dax" | "sql";
        code: string;
    } | null>(null);

    // Initialize LLM service when settings change
    useEffect(() => {
        const service = new LLMService(
            settings.general.backendUrl,
            settings.model.modelSelection
        );

        // Check connection
        service.healthCheck().then((isHealthy) => {
            setState((prev) => ({ ...prev, isConnected: isHealthy }));
            if (!isHealthy) {
                setState((prev) => ({
                    ...prev,
                    error: "Cannot connect to backend. Please check the Backend URL in settings.",
                }));
            }
        });

        setLLMService(service);
    }, [settings.general.backendUrl, settings.model.modelSelection]);

    // Add welcome message on first load
    useEffect(() => {
        if (state.messages.length === 0) {
            const welcomeMessage: ChatMessage = {
                id: "welcome",
                role: "assistant",
                content: `Welcome to BA Copilot! I can help you with:

• **Generate DAX measures** - Describe what you want to calculate
• **Write SQL queries** - Ask questions about your data
• **Explain data** - Get insights from your visualizations
• **Answer questions** - About your data model and business logic

${visualContext.hasData
    ? `I can see ${visualContext.rowCount} rows with ${visualContext.columns.length} columns in your current context.`
    : "Add some data to the visual to give me context about your report."}

How can I help you today?`,
                timestamp: new Date(),
                type: "text",
            };
            setState((prev) => ({ ...prev, messages: [welcomeMessage] }));
        }
    }, []);

    /**
     * Handle sending a message to the LLM
     */
    const handleSendMessage = useCallback(
        async (message: string) => {
            if (!llmService || !message.trim()) return;

            // Add user message
            const userMessage: ChatMessage = {
                id: `user-${Date.now()}`,
                role: "user",
                content: message,
                timestamp: new Date(),
                type: "text",
            };

            setState((prev) => ({
                ...prev,
                messages: [...prev.messages, userMessage],
                isLoading: true,
                error: null,
            }));

            try {
                // Prepare context for the API
                const context = {
                    columns: visualContext.columns,
                    rowCount: visualContext.rowCount,
                    sampleData: visualContext.sampleData,
                };

                // Call the API
                const response = await llmService.chat(message, context);

                // Create assistant message
                const assistantMessage: ChatMessage = {
                    id: `assistant-${Date.now()}`,
                    role: "assistant",
                    content: response.content,
                    timestamp: new Date(),
                    type: response.type,
                    metadata: {
                        dax: response.dax,
                        sql: response.sql,
                        sources: response.sources,
                    },
                };

                setState((prev) => ({
                    ...prev,
                    messages: [...prev.messages, assistantMessage],
                    isLoading: false,
                }));

                // If code was generated, show it in the code panel
                if (response.dax) {
                    setGeneratedCode({ type: "dax", code: response.dax });
                } else if (response.sql) {
                    setGeneratedCode({ type: "sql", code: response.sql });
                }
            } catch (error) {
                const errorMessage: ChatMessage = {
                    id: `error-${Date.now()}`,
                    role: "assistant",
                    content: `Sorry, I encountered an error: ${
                        error instanceof Error ? error.message : "Unknown error"
                    }. Please try again.`,
                    timestamp: new Date(),
                    type: "error",
                };

                setState((prev) => ({
                    ...prev,
                    messages: [...prev.messages, errorMessage],
                    isLoading: false,
                    error: error instanceof Error ? error.message : "Unknown error",
                }));
            }
        },
        [llmService, visualContext]
    );

    /**
     * Handle quick action button click
     */
    const handleQuickAction = useCallback(
        (prompt: string) => {
            handleSendMessage(prompt);
        },
        [handleSendMessage]
    );

    /**
     * Clear chat history
     */
    const handleClearChat = useCallback(() => {
        setState((prev) => ({
            ...prev,
            messages: [],
        }));
        setGeneratedCode(null);
    }, []);

    /**
     * Copy code to clipboard
     */
    const handleCopyCode = useCallback((code: string) => {
        navigator.clipboard.writeText(code).catch((err) => {
            console.error("Failed to copy code:", err);
        });
    }, []);

    // Calculate layout dimensions
    const containerStyle: React.CSSProperties = {
        width: `${width}px`,
        height: `${height}px`,
        display: "flex",
        flexDirection: "column",
        backgroundColor: settings.appearance.backgroundColor,
        color: settings.appearance.fontColor,
        fontSize: `${settings.appearance.fontSize}px`,
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        overflow: "hidden",
    };

    const chatHeight = Math.floor((height - 50) * (settings.appearance.chatHeight / 100));
    const codeHeight = height - 50 - chatHeight;

    // Show landing page if no backend URL configured
    if (!settings.general.backendUrl || settings.general.backendUrl === "http://localhost:8000") {
        return (
            <div style={containerStyle}>
                <LandingPage />
            </div>
        );
    }

    return (
        <div style={containerStyle} className="ba-copilot">
            <Header
                isConnected={state.isConnected}
                model={settings.model.modelSelection}
                onClearChat={handleClearChat}
            />

            <div className="ba-copilot__content">
                <div
                    className="ba-copilot__chat-section"
                    style={{ height: `${chatHeight}px` }}
                >
                    <QuickActions
                        onAction={handleQuickAction}
                        hasData={visualContext.hasData}
                    />
                    <ChatInterface
                        messages={state.messages}
                        isLoading={state.isLoading}
                        onSendMessage={handleSendMessage}
                        fontSize={settings.appearance.fontSize}
                    />
                </div>

                {generatedCode && codeHeight > 100 && (
                    <div
                        className="ba-copilot__code-section"
                        style={{ height: `${codeHeight}px` }}
                    >
                        <CodeDisplay
                            code={generatedCode.code}
                            language={generatedCode.type}
                            onCopy={() => handleCopyCode(generatedCode.code)}
                            onClear={() => setGeneratedCode(null)}
                        />
                    </div>
                )}
            </div>

            {state.error && (
                <div className="ba-copilot__error">
                    {state.error}
                </div>
            )}
        </div>
    );
};
