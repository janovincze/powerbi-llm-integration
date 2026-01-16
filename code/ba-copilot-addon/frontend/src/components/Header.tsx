/**
 * Header Component
 *
 * Displays the visual header with connection status and controls.
 */

import * as React from "react";

interface HeaderProps {
    isConnected: boolean;
    model: "sonnet" | "opus";
    onClearChat: () => void;
}

export const Header: React.FC<HeaderProps> = ({
    isConnected,
    model,
    onClearChat,
}) => {
    const modelLabel = model === "opus" ? "Claude Opus" : "Claude Sonnet";

    return (
        <div className="header">
            <div className="header__left">
                <span className="header__title">🤖 BA Copilot</span>
                <span className="header__model">{modelLabel}</span>
            </div>

            <div className="header__right">
                <span
                    className={`header__status ${
                        isConnected ? "header__status--connected" : "header__status--disconnected"
                    }`}
                    title={isConnected ? "Connected to backend" : "Not connected"}
                >
                    {isConnected ? "●" : "○"}
                </span>

                <button
                    className="header__button"
                    onClick={onClearChat}
                    title="Clear chat history"
                >
                    🗑️
                </button>
            </div>
        </div>
    );
};
