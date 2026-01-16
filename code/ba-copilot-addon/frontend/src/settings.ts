/**
 * Visual Settings
 *
 * Defines the configurable settings for the BA Copilot visual.
 * These settings appear in the Format pane in PowerBI.
 */

import powerbi from "powerbi-visuals-api";
import DataView = powerbi.DataView;

/**
 * General settings for backend configuration
 */
export class GeneralSettings {
    public backendUrl: string = "http://localhost:8000";
}

/**
 * Model settings for AI configuration
 */
export class ModelSettings {
    public modelSelection: "sonnet" | "opus" = "sonnet";
    public enableRAG: boolean = true;
}

/**
 * Appearance settings for visual customization
 */
export class AppearanceSettings {
    public chatHeight: number = 70;
    public fontSize: number = 12;
    public fontColor: string = "#333333";
    public backgroundColor: string = "#FFFFFF";
}

/**
 * Main settings class that aggregates all setting groups
 */
export class VisualSettings {
    public general: GeneralSettings = new GeneralSettings();
    public model: ModelSettings = new ModelSettings();
    public appearance: AppearanceSettings = new AppearanceSettings();

    /**
     * Parse settings from the data view
     */
    public static parse(dataView: DataView): VisualSettings {
        const settings = new VisualSettings();

        if (!dataView || !dataView.metadata || !dataView.metadata.objects) {
            return settings;
        }

        const objects = dataView.metadata.objects;

        // Parse general settings
        if (objects.general) {
            settings.general.backendUrl =
                (objects.general.backendUrl as string) || settings.general.backendUrl;
        }

        // Parse model settings
        if (objects.model) {
            settings.model.modelSelection =
                (objects.model.modelSelection as "sonnet" | "opus") || settings.model.modelSelection;
            settings.model.enableRAG =
                objects.model.enableRAG !== undefined
                    ? (objects.model.enableRAG as boolean)
                    : settings.model.enableRAG;
        }

        // Parse appearance settings
        if (objects.appearance) {
            settings.appearance.chatHeight =
                (objects.appearance.chatHeight as number) || settings.appearance.chatHeight;
            settings.appearance.fontSize =
                (objects.appearance.fontSize as number) || settings.appearance.fontSize;

            const fontColorObj = objects.appearance.fontColor as { solid?: { color?: string } };
            if (fontColorObj?.solid?.color) {
                settings.appearance.fontColor = fontColorObj.solid.color;
            }

            const bgColorObj = objects.appearance.backgroundColor as { solid?: { color?: string } };
            if (bgColorObj?.solid?.color) {
                settings.appearance.backgroundColor = bgColorObj.solid.color;
            }
        }

        return settings;
    }

    /**
     * Get the formatting model for the Format pane
     */
    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return {
            cards: [
                {
                    displayName: "General",
                    uid: "general_card",
                    groups: [
                        {
                            displayName: "Connection",
                            uid: "general_connection",
                            slices: [
                                {
                                    uid: "general_backendUrl",
                                    displayName: "Backend URL",
                                    control: {
                                        type: powerbi.visuals.FormattingComponent.TextInput,
                                        properties: {
                                            descriptor: {
                                                objectName: "general",
                                                propertyName: "backendUrl",
                                            },
                                            value: this.general.backendUrl,
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                },
                {
                    displayName: "AI Model",
                    uid: "model_card",
                    groups: [
                        {
                            displayName: "Configuration",
                            uid: "model_config",
                            slices: [
                                {
                                    uid: "model_selection",
                                    displayName: "Model",
                                    control: {
                                        type: powerbi.visuals.FormattingComponent.Dropdown,
                                        properties: {
                                            descriptor: {
                                                objectName: "model",
                                                propertyName: "modelSelection",
                                            },
                                            value: this.model.modelSelection,
                                        },
                                    },
                                },
                                {
                                    uid: "model_rag",
                                    displayName: "Enable Knowledge Base",
                                    control: {
                                        type: powerbi.visuals.FormattingComponent.ToggleSwitch,
                                        properties: {
                                            descriptor: {
                                                objectName: "model",
                                                propertyName: "enableRAG",
                                            },
                                            value: this.model.enableRAG,
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                },
                {
                    displayName: "Appearance",
                    uid: "appearance_card",
                    groups: [
                        {
                            displayName: "Style",
                            uid: "appearance_style",
                            slices: [
                                {
                                    uid: "appearance_fontSize",
                                    displayName: "Font Size",
                                    control: {
                                        type: powerbi.visuals.FormattingComponent.NumUpDown,
                                        properties: {
                                            descriptor: {
                                                objectName: "appearance",
                                                propertyName: "fontSize",
                                            },
                                            value: this.appearance.fontSize,
                                        },
                                    },
                                },
                                {
                                    uid: "appearance_fontColor",
                                    displayName: "Font Color",
                                    control: {
                                        type: powerbi.visuals.FormattingComponent.ColorPicker,
                                        properties: {
                                            descriptor: {
                                                objectName: "appearance",
                                                propertyName: "fontColor",
                                            },
                                            value: { value: this.appearance.fontColor },
                                        },
                                    },
                                },
                                {
                                    uid: "appearance_backgroundColor",
                                    displayName: "Background Color",
                                    control: {
                                        type: powerbi.visuals.FormattingComponent.ColorPicker,
                                        properties: {
                                            descriptor: {
                                                objectName: "appearance",
                                                propertyName: "backgroundColor",
                                            },
                                            value: { value: this.appearance.backgroundColor },
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                },
            ],
        };
    }
}
