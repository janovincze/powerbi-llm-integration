/**
 * Type Definitions for BA Copilot Visual
 */

import powerbi from "powerbi-visuals-api";
import { VisualSettings } from "./settings";

/**
 * Column information extracted from the data view
 */
export interface DataColumn {
    name: string;
    type: string;
    queryName: string;
}

/**
 * Context information passed to the React app
 */
export interface VisualContext {
    columns: DataColumn[];
    rowCount: number;
    hasData: boolean;
    sampleData?: Record<string, unknown>[];
    metadata?: {
        reportName?: string;
    };
}

/**
 * Props for the main App component
 */
export interface AppProps {
    width: number;
    height: number;
    settings: VisualSettings;
    visualContext: VisualContext;
    host: powerbi.extensibility.visual.IVisualHost;
}

/**
 * Chat message structure
 */
export interface ChatMessage {
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
    timestamp: Date;
    type?: "text" | "dax" | "sql" | "error";
    metadata?: {
        dax?: string;
        sql?: string;
        sources?: string[];
        tokens?: {
            input: number;
            output: number;
        };
    };
}

/**
 * Response from the backend chat API
 */
export interface ChatResponse {
    content: string;
    type: "text" | "dax" | "sql";
    dax?: string;
    sql?: string;
    sources?: string[];
}

/**
 * Response from the DAX generation API
 */
export interface DAXResponse {
    dax: string;
    explanation: string;
    valid: boolean;
    warnings: string[];
}

/**
 * Quick action button definition
 */
export interface QuickAction {
    id: string;
    label: string;
    icon: string;
    prompt: string;
    category: "dax" | "sql" | "insight" | "help";
}

/**
 * Application state
 */
export interface AppState {
    messages: ChatMessage[];
    isLoading: boolean;
    error: string | null;
    isConnected: boolean;
    activeTab: "chat" | "history" | "settings";
}
