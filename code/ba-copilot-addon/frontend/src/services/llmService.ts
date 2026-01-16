/**
 * LLM Service
 *
 * Handles communication with the BA Copilot backend API.
 */

import axios, { AxiosInstance, AxiosError } from "axios";
import { ChatResponse, DAXResponse } from "../types";

export class LLMService {
    private client: AxiosInstance;
    private model: "sonnet" | "opus";

    constructor(baseUrl: string, model: "sonnet" | "opus" = "sonnet") {
        this.model = model;

        this.client = axios.create({
            baseURL: baseUrl,
            timeout: 60000, // 60 second timeout for LLM calls
            headers: {
                "Content-Type": "application/json",
            },
        });

        // Add response interceptor for error handling
        this.client.interceptors.response.use(
            (response) => response,
            (error: AxiosError) => {
                if (error.response) {
                    // Server responded with error
                    const message =
                        (error.response.data as { detail?: string })?.detail ||
                        error.message;
                    throw new Error(`API Error: ${message}`);
                } else if (error.request) {
                    // No response received
                    throw new Error(
                        "Cannot connect to backend. Please check the URL and try again."
                    );
                } else {
                    throw new Error(`Request Error: ${error.message}`);
                }
            }
        );
    }

    /**
     * Check if the backend is healthy
     */
    async healthCheck(): Promise<boolean> {
        try {
            const response = await this.client.get("/health", { timeout: 5000 });
            return response.status === 200;
        } catch {
            return false;
        }
    }

    /**
     * Send a chat message and get a response
     */
    async chat(
        message: string,
        context: Record<string, unknown>
    ): Promise<ChatResponse> {
        const response = await this.client.post<ChatResponse>("/api/chat", {
            message,
            context,
            model: this.model,
        });

        return response.data;
    }

    /**
     * Generate DAX from natural language
     */
    async generateDAX(
        question: string,
        schema: Record<string, unknown>
    ): Promise<DAXResponse> {
        const response = await this.client.post<DAXResponse>("/api/generate-dax", {
            question,
            schema,
        });

        return response.data;
    }

    /**
     * Validate a DAX expression
     */
    async validateDAX(dax: string): Promise<{
        valid: boolean;
        errors: string[];
        warnings: string[];
    }> {
        const response = await this.client.post("/api/validate-dax", { dax });
        return response.data;
    }

    /**
     * Generate a summary of data
     */
    async summarizeData(
        data: Record<string, unknown>,
        focus?: string
    ): Promise<string> {
        const response = await this.client.post<{ summary: string }>(
            "/api/summarize",
            {
                data,
                focus,
            }
        );

        return response.data.summary;
    }

    /**
     * Get explanation for a DAX expression
     */
    async explainDAX(dax: string): Promise<string> {
        const response = await this.client.post<{ explanation: string }>(
            "/api/explain-dax",
            { dax }
        );

        return response.data.explanation;
    }
}
