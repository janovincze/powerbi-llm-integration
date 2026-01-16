/**
 * Code Display Component
 *
 * Displays generated DAX or SQL code with syntax highlighting
 * and copy functionality.
 */

import * as React from "react";
import { useState, useCallback } from "react";

interface CodeDisplayProps {
    code: string;
    language: "dax" | "sql";
    onCopy: () => void;
    onClear: () => void;
}

export const CodeDisplay: React.FC<CodeDisplayProps> = ({
    code,
    language,
    onCopy,
    onClear,
}) => {
    const [copied, setCopied] = useState(false);

    /**
     * Handle copy button click
     */
    const handleCopy = useCallback(() => {
        onCopy();
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    }, [onCopy]);

    /**
     * Basic syntax highlighting for DAX
     */
    const highlightDAX = (code: string): React.ReactNode => {
        const keywords = [
            "VAR",
            "RETURN",
            "CALCULATE",
            "FILTER",
            "ALL",
            "ALLEXCEPT",
            "SUM",
            "SUMX",
            "AVERAGE",
            "AVERAGEX",
            "COUNT",
            "COUNTROWS",
            "DIVIDE",
            "IF",
            "SWITCH",
            "TRUE",
            "FALSE",
            "BLANK",
            "ISBLANK",
            "RELATED",
            "RELATEDTABLE",
            "SELECTEDVALUE",
            "HASONEVALUE",
            "TOTALMTD",
            "TOTALYTD",
            "TOTALQTD",
            "SAMEPERIODLASTYEAR",
            "DATEADD",
            "DATESINPERIOD",
            "MAX",
            "MIN",
            "MAXX",
            "MINX",
            "FORMAT",
        ];

        // Simple regex-based highlighting
        let highlighted = code;

        // Highlight keywords
        keywords.forEach((keyword) => {
            const regex = new RegExp(`\\b(${keyword})\\b`, "gi");
            highlighted = highlighted.replace(
                regex,
                '<span class="code-keyword">$1</span>'
            );
        });

        // Highlight strings
        highlighted = highlighted.replace(
            /"([^"]*)"/g,
            '<span class="code-string">"$1"</span>'
        );

        // Highlight comments
        highlighted = highlighted.replace(
            /(\/\/.*$)/gm,
            '<span class="code-comment">$1</span>'
        );

        // Highlight numbers
        highlighted = highlighted.replace(
            /\b(\d+\.?\d*)\b/g,
            '<span class="code-number">$1</span>'
        );

        // Highlight column references [Column]
        highlighted = highlighted.replace(
            /(\[[^\]]+\])/g,
            '<span class="code-column">$1</span>'
        );

        // Highlight table references 'Table'
        highlighted = highlighted.replace(
            /('([^']+)')/g,
            '<span class="code-table">$1</span>'
        );

        return <span dangerouslySetInnerHTML={{ __html: highlighted }} />;
    };

    /**
     * Basic syntax highlighting for SQL
     */
    const highlightSQL = (code: string): React.ReactNode => {
        const keywords = [
            "SELECT",
            "FROM",
            "WHERE",
            "JOIN",
            "INNER",
            "LEFT",
            "RIGHT",
            "OUTER",
            "ON",
            "AND",
            "OR",
            "NOT",
            "IN",
            "BETWEEN",
            "LIKE",
            "IS",
            "NULL",
            "AS",
            "ORDER",
            "BY",
            "GROUP",
            "HAVING",
            "LIMIT",
            "OFFSET",
            "UNION",
            "INSERT",
            "UPDATE",
            "DELETE",
            "CREATE",
            "ALTER",
            "DROP",
            "TABLE",
            "INDEX",
            "VIEW",
            "DISTINCT",
            "COUNT",
            "SUM",
            "AVG",
            "MIN",
            "MAX",
            "CASE",
            "WHEN",
            "THEN",
            "ELSE",
            "END",
            "WITH",
            "CTE",
            "OVER",
            "PARTITION",
            "ROW_NUMBER",
            "RANK",
            "DENSE_RANK",
            "COALESCE",
            "NULLIF",
            "CAST",
            "CONVERT",
        ];

        let highlighted = code;

        // Highlight keywords
        keywords.forEach((keyword) => {
            const regex = new RegExp(`\\b(${keyword})\\b`, "gi");
            highlighted = highlighted.replace(
                regex,
                '<span class="code-keyword">$1</span>'
            );
        });

        // Highlight strings
        highlighted = highlighted.replace(
            /'([^']*)'/g,
            '<span class="code-string">\'$1\'</span>'
        );

        // Highlight comments
        highlighted = highlighted.replace(
            /(--.*$)/gm,
            '<span class="code-comment">$1</span>'
        );

        // Highlight numbers
        highlighted = highlighted.replace(
            /\b(\d+\.?\d*)\b/g,
            '<span class="code-number">$1</span>'
        );

        return <span dangerouslySetInnerHTML={{ __html: highlighted }} />;
    };

    const highlightedCode =
        language === "dax" ? highlightDAX(code) : highlightSQL(code);

    return (
        <div className="code-display">
            <div className="code-display__header">
                <span className="code-display__language">
                    {language.toUpperCase()}
                </span>
                <div className="code-display__actions">
                    <button
                        className="code-action-button"
                        onClick={handleCopy}
                        title="Copy to clipboard"
                    >
                        {copied ? "✓ Copied" : "📋 Copy"}
                    </button>
                    <button
                        className="code-action-button code-action-button--close"
                        onClick={onClear}
                        title="Close"
                    >
                        ✕
                    </button>
                </div>
            </div>
            <pre className="code-display__content">
                <code>{highlightedCode}</code>
            </pre>
        </div>
    );
};
