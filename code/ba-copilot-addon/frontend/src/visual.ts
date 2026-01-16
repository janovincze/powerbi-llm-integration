/**
 * BA Copilot Visual - Main Entry Point
 *
 * This is the main class that PowerBI instantiates for the custom visual.
 * It handles data binding, settings, and renders the React application.
 */

import powerbi from "powerbi-visuals-api";
import * as React from "react";
import * as ReactDOM from "react-dom";

import { App } from "./components/App";
import { VisualSettings } from "./settings";
import { VisualContext, DataColumn } from "./types";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualHost = powerbi.extensibility.visual.IVisualHost;
import DataView = powerbi.DataView;

import "../style/visual.less";

export class Visual implements IVisual {
    private target: HTMLElement;
    private host: IVisualHost;
    private settings: VisualSettings;
    private isLandingPageOn: boolean;
    private landingPageRemoved: boolean;

    constructor(options: VisualConstructorOptions) {
        this.target = options.element;
        this.host = options.host;
        this.isLandingPageOn = false;
        this.landingPageRemoved = false;

        // Set up container styling
        this.target.style.overflow = "hidden";
        this.target.style.height = "100%";
        this.target.style.width = "100%";
    }

    /**
     * Called when the visual is updated (data change, resize, etc.)
     */
    public update(options: VisualUpdateOptions): void {
        // Parse settings from data view
        if (options.dataViews && options.dataViews[0]) {
            this.settings = VisualSettings.parse(options.dataViews[0]);

            // Handle landing page
            this.handleLandingPage(options);

            // Extract context from visual data
            const visualContext = this.extractContext(options);

            // Render React application
            this.renderApp(options.viewport, visualContext);
        } else {
            // No data - show landing page or empty state
            this.renderEmptyState(options.viewport);
        }
    }

    /**
     * Handle landing page display logic
     */
    private handleLandingPage(options: VisualUpdateOptions): void {
        if (!options.dataViews || !options.dataViews[0]?.metadata?.columns?.length) {
            if (!this.isLandingPageOn) {
                this.isLandingPageOn = true;
                this.landingPageRemoved = false;
            }
        } else {
            if (this.isLandingPageOn && !this.landingPageRemoved) {
                this.isLandingPageOn = false;
                this.landingPageRemoved = true;
            }
        }
    }

    /**
     * Extract context information from the visual's data view
     */
    private extractContext(options: VisualUpdateOptions): VisualContext {
        const dataView = options.dataViews?.[0];

        if (!dataView || !dataView.table) {
            return {
                columns: [],
                rowCount: 0,
                hasData: false,
            };
        }

        const columns: DataColumn[] = dataView.table.columns.map((col) => ({
            name: col.displayName,
            type: this.getColumnType(col),
            queryName: col.queryName || col.displayName,
        }));

        const sampleData = this.extractSampleData(dataView.table, 5);

        return {
            columns,
            rowCount: dataView.table.rows?.length || 0,
            hasData: true,
            sampleData,
            metadata: {
                reportName: dataView.metadata?.objects?.general?.reportName as string,
            },
        };
    }

    /**
     * Get the string type name for a column
     */
    private getColumnType(column: powerbi.DataViewMetadataColumn): string {
        if (column.type?.numeric) return "numeric";
        if (column.type?.dateTime) return "datetime";
        if (column.type?.bool) return "boolean";
        if (column.type?.text) return "text";
        return "unknown";
    }

    /**
     * Extract sample data rows for context
     */
    private extractSampleData(
        table: powerbi.DataViewTable,
        limit: number
    ): Record<string, unknown>[] {
        if (!table.rows || table.rows.length === 0) {
            return [];
        }

        const columns = table.columns.map((c) => c.displayName);
        const sampleRows = table.rows.slice(0, limit);

        return sampleRows.map((row) => {
            const record: Record<string, unknown> = {};
            columns.forEach((col, idx) => {
                record[col] = row[idx];
            });
            return record;
        });
    }

    /**
     * Render the React application
     */
    private renderApp(
        viewport: powerbi.IViewport,
        visualContext: VisualContext
    ): void {
        const appProps = {
            width: viewport.width,
            height: viewport.height,
            settings: this.settings,
            visualContext,
            host: this.host,
        };

        ReactDOM.render(
            React.createElement(App, appProps),
            this.target
        );
    }

    /**
     * Render empty state when no data is available
     */
    private renderEmptyState(viewport: powerbi.IViewport): void {
        const emptyContext: VisualContext = {
            columns: [],
            rowCount: 0,
            hasData: false,
        };

        this.renderApp(viewport, emptyContext);
    }

    /**
     * Returns properties for the formatting pane
     */
    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return this.settings?.getFormattingModel() || { cards: [] };
    }

    /**
     * Cleanup when visual is destroyed
     */
    public destroy(): void {
        ReactDOM.unmountComponentAtNode(this.target);
    }
}
