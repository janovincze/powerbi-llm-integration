/**
 * Landing Page Component
 *
 * Displayed when the visual is first added or not configured.
 */

import * as React from "react";

export const LandingPage: React.FC = () => {
    return (
        <div className="landing-page">
            <div className="landing-page__icon">🤖</div>
            <h2 className="landing-page__title">BA Copilot</h2>
            <p className="landing-page__subtitle">
                AI-powered assistant for Business Analysts
            </p>

            <div className="landing-page__setup">
                <h3>Setup Required</h3>
                <ol className="landing-page__steps">
                    <li>
                        <strong>Deploy the backend service</strong>
                        <p>
                            Run the BA Copilot backend on your server or Azure.
                            See the documentation for deployment instructions.
                        </p>
                    </li>
                    <li>
                        <strong>Configure the Backend URL</strong>
                        <p>
                            Open the Format pane and enter your backend URL
                            under General → Backend URL.
                        </p>
                    </li>
                    <li>
                        <strong>Add data to the visual</strong>
                        <p>
                            Drag fields to the visual to give the AI context
                            about your data model.
                        </p>
                    </li>
                </ol>
            </div>

            <div className="landing-page__features">
                <h3>Features</h3>
                <div className="landing-page__feature-grid">
                    <div className="landing-page__feature">
                        <span className="landing-page__feature-icon">📝</span>
                        <span className="landing-page__feature-label">
                            Generate DAX
                        </span>
                    </div>
                    <div className="landing-page__feature">
                        <span className="landing-page__feature-icon">🔍</span>
                        <span className="landing-page__feature-label">
                            Write SQL
                        </span>
                    </div>
                    <div className="landing-page__feature">
                        <span className="landing-page__feature-icon">💡</span>
                        <span className="landing-page__feature-label">
                            Get Insights
                        </span>
                    </div>
                    <div className="landing-page__feature">
                        <span className="landing-page__feature-icon">📚</span>
                        <span className="landing-page__feature-label">
                            Knowledge Base
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
};
