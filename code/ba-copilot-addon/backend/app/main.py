"""
BA Copilot Backend Service

FastAPI server providing LLM-powered features for the PowerBI custom visual.
"""

import os
from typing import Optional, Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic

from services.rag_pipeline import RAGPipeline
from services.dax_validator import DAXValidator


# Initialize FastAPI app
app = FastAPI(
    title="BA Copilot Backend",
    description="LLM-powered backend for PowerBI Business Analyst assistant",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
claude = anthropic.Anthropic()
rag = RAGPipeline()
dax_validator = DAXValidator()


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    context: dict
    model: Literal["sonnet", "opus"] = "sonnet"


class ChatResponse(BaseModel):
    content: str
    type: Literal["text", "dax", "sql"]
    dax: Optional[str] = None
    sql: Optional[str] = None
    sources: Optional[list[str]] = None


class DAXRequest(BaseModel):
    question: str
    schema: dict


class DAXResponse(BaseModel):
    dax: str
    explanation: str
    valid: bool
    warnings: list[str] = []


class ValidateDAXRequest(BaseModel):
    dax: str


class SummarizeRequest(BaseModel):
    data: dict
    focus: Optional[str] = None


# Model mapping
MODEL_MAP = {
    "sonnet": "claude-sonnet-4-20250514",
    "opus": "claude-opus-4-20250514",
}


def get_system_prompt(rag_context: list[str], visual_context: dict) -> str:
    """Build the system prompt with context."""
    context_str = "\n\n".join(rag_context) if rag_context else "No additional context available."

    return f"""You are a Business Intelligence assistant helping analysts work with PowerBI.

Your capabilities:
- Generate DAX measures from natural language
- Create SQL queries for data exploration
- Explain data patterns and insights
- Suggest visualization improvements

Context from Knowledge Base:
{context_str}

Visual Context:
{visual_context}

Guidelines:
- Be concise and actionable
- When generating code, use proper formatting
- Explain your reasoning
- Suggest improvements when appropriate"""


def extract_code_block(text: str, language: str) -> Optional[str]:
    """Extract code block from markdown-formatted response."""
    import re

    # Try to find fenced code block
    pattern = rf"```{language}?\s*(.*?)```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # If no fenced block, try to detect code-like content
    if language == "dax":
        # Look for DAX patterns
        if "=" in text and any(kw in text.upper() for kw in ["VAR", "RETURN", "CALCULATE", "SUM", "AVERAGE"]):
            lines = text.split("\n")
            code_lines = []
            in_code = False
            for line in lines:
                if "=" in line and not in_code:
                    in_code = True
                if in_code:
                    if line.strip() and not line.startswith("**") and not line.startswith("#"):
                        code_lines.append(line)
                    elif not line.strip() and code_lines:
                        break
            if code_lines:
                return "\n".join(code_lines)

    return None


def classify_response_type(content: str) -> Literal["text", "dax", "sql"]:
    """Classify the response type based on content."""
    content_lower = content.lower()

    if "```dax" in content_lower or ("measure" in content_lower and "=" in content):
        return "dax"
    if "```sql" in content_lower or "select" in content_lower:
        return "sql"
    return "text"


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for conversational interaction.
    """
    try:
        # Retrieve relevant context from RAG
        rag_context = rag.retrieve(request.message, k=3)

        # Build system prompt
        system_prompt = get_system_prompt(rag_context, request.context)

        # Get model ID
        model_id = MODEL_MAP.get(request.model, MODEL_MAP["sonnet"])

        # Call Claude
        response = claude.messages.create(
            model=model_id,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": request.message}],
        )

        content = response.content[0].text

        # Classify response type
        response_type = classify_response_type(content)

        # Extract code if present
        dax_code = None
        sql_code = None

        if response_type == "dax":
            dax_code = extract_code_block(content, "dax")
        elif response_type == "sql":
            sql_code = extract_code_block(content, "sql")

        return ChatResponse(
            content=content,
            type=response_type,
            dax=dax_code,
            sql=sql_code,
            sources=[doc[:100] + "..." for doc in rag_context] if rag_context else None,
        )

    except anthropic.APIError as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-dax", response_model=DAXResponse)
async def generate_dax(request: DAXRequest):
    """
    Generate DAX measure from natural language.
    """
    prompt = f"""Generate a DAX measure for this business requirement:

Requirement: {request.question}

Available Schema:
{request.schema}

Best Practices to Follow:
- Use variables (VAR/RETURN) for clarity
- Avoid nested CALCULATE when possible
- Add inline comments for complex logic
- Consider filter context implications
- Use appropriate data types

Return the DAX code in a ```dax code block, followed by a brief explanation."""

    try:
        response = claude.messages.create(
            model=MODEL_MAP["sonnet"],
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text
        dax_code = extract_code_block(content, "dax") or content

        # Validate the generated DAX
        validation = dax_validator.validate(dax_code)

        # Extract explanation (everything after the code block)
        explanation = content.split("```")[-1].strip() if "```" in content else ""

        return DAXResponse(
            dax=dax_code,
            explanation=explanation,
            valid=validation.is_valid,
            warnings=validation.warnings,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/validate-dax")
async def validate_dax(request: ValidateDAXRequest):
    """
    Validate DAX syntax.
    """
    validation = dax_validator.validate(request.dax)
    return {
        "valid": validation.is_valid,
        "errors": validation.errors,
        "warnings": validation.warnings,
    }


@app.post("/api/summarize")
async def summarize_data(request: SummarizeRequest):
    """
    Generate natural language summary of data.
    """
    focus = request.focus or "general patterns and insights"

    prompt = f"""Analyze this data and provide a concise summary:

Data:
{request.data}

Focus on: {focus}

Provide:
1. Key observations (2-3 bullet points)
2. Notable patterns or anomalies
3. One actionable recommendation

Keep the response brief and executive-friendly."""

    try:
        response = claude.messages.create(
            model=MODEL_MAP["sonnet"],
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        return {"summary": response.content[0].text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/explain-dax")
async def explain_dax(dax: str):
    """
    Explain what a DAX measure does.
    """
    prompt = f"""Explain this DAX measure in plain English:

```dax
{dax}
```

Provide:
1. What it calculates
2. How it handles filter context
3. Any potential issues or improvements"""

    try:
        response = claude.messages.create(
            model=MODEL_MAP["sonnet"],
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        return {"explanation": response.content[0].text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENV", "development") == "development",
    )
