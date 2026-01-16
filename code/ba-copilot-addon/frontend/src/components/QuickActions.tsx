/**
 * Quick Actions Component
 *
 * Provides quick action buttons for common tasks.
 */

import * as React from "react";
import { useCallback } from "react";
import { QuickAction } from "../types";

interface QuickActionsProps {
    onAction: (prompt: string) => void;
    hasData: boolean;
}

const QUICK_ACTIONS: QuickAction[] = [
    {
        id: "yoy-measure",
        label: "YoY Growth",
        icon: "📈",
        prompt: "Create a DAX measure that calculates year-over-year growth percentage",
        category: "dax",
    },
    {
        id: "mtd-measure",
        label: "MTD Total",
        icon: "📅",
        prompt: "Create a DAX measure for month-to-date total",
        category: "dax",
    },
    {
        id: "top-10",
        label: "Top 10",
        icon: "🏆",
        prompt: "Write a SQL query to find the top 10 items by value",
        category: "sql",
    },
    {
        id: "summarize",
        label: "Summarize",
        icon: "📊",
        prompt: "Analyze and summarize the key insights from the current data",
        category: "insight",
    },
    {
        id: "explain-data",
        label: "Explain Data",
        icon: "🔍",
        prompt: "Explain the columns and data types in the current dataset",
        category: "insight",
    },
    {
        id: "help",
        label: "Help",
        icon: "❓",
        prompt: "What can you help me with? Show me some examples.",
        category: "help",
    },
];

export const QuickActions: React.FC<QuickActionsProps> = ({
    onAction,
    hasData,
}) => {
    const handleClick = useCallback(
        (action: QuickAction) => {
            onAction(action.prompt);
        },
        [onAction]
    );

    // Filter actions based on whether we have data
    const availableActions = hasData
        ? QUICK_ACTIONS
        : QUICK_ACTIONS.filter((a) => a.category === "help");

    return (
        <div className="quick-actions">
            <div className="quick-actions__label">Quick Actions:</div>
            <div className="quick-actions__buttons">
                {availableActions.map((action) => (
                    <button
                        key={action.id}
                        className={`quick-action-button quick-action-button--${action.category}`}
                        onClick={() => handleClick(action)}
                        title={action.prompt}
                    >
                        <span className="quick-action-button__icon">{action.icon}</span>
                        <span className="quick-action-button__label">{action.label}</span>
                    </button>
                ))}
            </div>
        </div>
    );
};
