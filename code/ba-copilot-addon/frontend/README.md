# BA Copilot - PowerBI Custom Visual

AI-powered assistant for Business Analysts working with PowerBI.

## Features

- **Natural Language to DAX**: Describe what you want to calculate, get DAX measures
- **SQL Query Generation**: Ask questions about your data in plain English
- **Data Insights**: Get AI-powered analysis and summaries
- **Knowledge Base Integration**: Answers enriched with company documentation

## Prerequisites

- Node.js 18+
- PowerBI Desktop
- BA Copilot Backend running (see `../backend/`)

## Development Setup

```bash
# Install dependencies
npm install

# Start development server
npm run start

# This will:
# 1. Start pbiviz development server on https://localhost:8080
# 2. Watch for file changes and rebuild
```

## Testing in PowerBI Desktop

1. Open PowerBI Desktop
2. Go to **File → Options and Settings → Options**
3. Under **Security**, enable **Developer visual**
4. In your report, add the Developer Visual from the Visualizations pane
5. The visual will auto-reload when you make changes

## Building for Production

```bash
# Create production package
npm run package

# Output: dist/BACopilot.pbiviz
```

## Installing the Visual

### Method 1: Import from File
1. In PowerBI Desktop, click **...** in the Visualizations pane
2. Select **Import a visual from a file**
3. Choose the `.pbiviz` file

### Method 2: Organizational Visuals
1. Upload the `.pbiviz` to your PowerBI Admin Portal
2. Users can then add it from **My organization** in the Visualizations pane

## Configuration

In the Format pane, configure:

| Setting | Description |
|---------|-------------|
| Backend URL | URL of your BA Copilot backend service |
| Model | Claude Sonnet (fast) or Claude Opus (powerful) |
| Enable Knowledge Base | Use RAG for context-aware responses |

## Project Structure

```
src/
├── visual.ts           # Main PowerBI visual class
├── settings.ts         # Visual settings/options
├── types.ts            # TypeScript type definitions
├── components/
│   ├── App.tsx         # Root React component
│   ├── ChatInterface.tsx
│   ├── QuickActions.tsx
│   ├── CodeDisplay.tsx
│   ├── Header.tsx
│   └── LandingPage.tsx
├── services/
│   └── llmService.ts   # Backend API client
style/
└── visual.less         # LESS styles
```

## Troubleshooting

### Visual not loading
- Check that the backend URL is correct in settings
- Verify the backend is running and accessible
- Check browser console for errors

### CORS errors
- Ensure the backend has the correct CORS configuration
- The visual runs in an iframe, so cross-origin requests must be allowed

### Authentication issues
- If using Azure, ensure proper Entra ID configuration
- Check that API keys are set in the backend

## License

MIT
