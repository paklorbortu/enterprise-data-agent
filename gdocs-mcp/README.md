# Google Docs MCP Server

A comprehensive Model Context Protocol (MCP) server that provides professional-grade Google Docs integration through Claude. This server enables advanced document creation, editing, formatting, and management capabilities.

## 🚀 Features

### Core Document Operations
- **Document Management**: Create, read, update, delete, and search documents
- **Advanced Reading**: Support for text, JSON, and Markdown output formats
- **Content Manipulation**: Insert, delete, and modify text at specific positions

### Advanced Formatting
- **Text Styling**: Bold, italic, underline, strikethrough, colors, fonts, links
- **Paragraph Styling**: Headings, alignment, indentation, spacing
- **List Management**: Bullet points, numbered lists, alphabetical, Roman numerals

### Content Structure
- **Page Breaks**: Insert page breaks for document structure
- **Content Ranges**: Precise text selection and manipulation
- **Professional Templates**: Pre-configured prompts for common document types

### Smart Prompts
- **Document Creation**: Intelligent prompts for creating various document types
- **Document Analysis**: Analyze existing documents for content and structure
- **Document Formatting**: Apply professional formatting styles automatically

## 📁 Project Structure

The project is organized into a modular architecture for maintainability and extensibility:

```
src/
├── server.ts              # Main server entry point
├── types.ts               # Shared TypeScript interfaces and types
├── auth.ts                # Google OAuth2 authentication logic
├── resources.ts           # Document listing and retrieval resources
├── prompts.ts             # Pre-configured prompts for common operations
└── tools/                 # Tool implementations organized by category
    ├── index.ts           # Central tool registration
    ├── basic-tools.ts     # Core document CRUD operations
    ├── formatting-tools.ts # Text and paragraph formatting
    └── content-tools.ts   # Content manipulation and structure
```

### Architecture Benefits
- **Modular Design**: Each tool category is in its own file for easy maintenance
- **Type Safety**: Comprehensive TypeScript interfaces for all operations
- **Extensibility**: Easy to add new tools by creating new modules
- **Separation of Concerns**: Authentication, resources, and tools are clearly separated
- **Professional Code Quality**: Strict TypeScript configuration with proper error handling

## 🛠 Prerequisites

- **Node.js**: v18.0.0 or later
- **Google Cloud Project**: With Google Docs API and Google Drive API enabled
- **OAuth 2.0 Credentials**: Desktop application credentials from Google Cloud Console

## ⚙️ Setup

### 1. Clone and Install

```bash
git clone https://github.com/olpetit/gdocs-mcp.git
cd gdocs-mcp
npm install
```

### 2. Google Cloud Configuration

1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable APIs**:
   - Enable Google Docs API
   - Enable Google Drive API

3. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" for application type
   - Download the JSON file and save as `credentials.json` in project root

### 3. Build and Run

```bash
# Build the project
npm run build

# Start the server
npm start

# Or run in development mode
npm run dev
```

## 🔧 Available Scripts

- `npm run build` - Compile TypeScript to JavaScript
- `npm run build:watch` - Watch mode for development
- `npm start` - Start the compiled server
- `npm run dev` - Build and start in one command
- `npm run clean` - Remove build directory
- `npm run rebuild` - Clean and rebuild
- `npm run type-check` - Type check without compilation

## 📋 Available Tools

### Basic Document Operations
- `create-doc` - Create new documents with optional initial content
- `update-doc` - Update existing documents (append or replace)
- `search-docs` - Search documents by content
- `delete-doc` - Delete documents
- `read-doc-advanced` - Read documents in multiple formats (text, JSON, markdown)

### Formatting Tools
- `apply-text-style` - Apply text formatting (bold, italic, colors, fonts, links)
- `apply-paragraph-style` - Apply paragraph formatting (headings, alignment, indentation)
- `apply-list-style` - Convert text to various list formats (bullet, numbered, alpha, roman)

### Content Manipulation
- `insert-text-at-index` - Insert text at specific positions
- `delete-range` - Delete specific text ranges
- `insert-page-break` - Insert page breaks
- `list-comments` - List comments from documents (API limitation noted)
- `add-comment` - Add comments to documents (API limitation noted)

## 🎯 Available Prompts

### Document Creation
- `create-document` - Intelligent document creation with customizable parameters:
  - Document type (report, letter, memo, proposal, etc.)
  - Writing style (formal, casual, academic, professional)
  - Target audience specification
  - Table of contents inclusion
  - Automatic formatting application

### Document Analysis
- `analyze-doc` - Analyze existing documents for:
  - Content summary and structure
  - Key points identification
  - Improvement suggestions

### Document Formatting
- `format-document` - Apply professional formatting styles:
  - Academic, business, creative, or technical styles
  - Automatic markdown cleanup
  - Native Google Docs formatting application

## 🎯 Usage Examples

### Creating a Professional Document

```typescript
// 1. Create document with initial content
await createDoc({
  title: "Q4 Business Report",
  content: "Executive Summary\n\nThis report covers our Q4 performance..."
});

// 2. Add more content at specific position
await insertTextAtIndex({
  docId: "document_id",
  textToInsert: "\n\nKey Findings:\n",
  index: 50
});

// 3. Apply heading styles
await applyParagraphStyle({
  docId: "document_id",
  textToFind: "Executive Summary",
  namedStyleType: "HEADING_1"
});

// 4. Format important text
await applyTextStyle({
  docId: "document_id",
  textToFind: "Important Note",
  bold: true,
  foregroundColor: "#FF0000"
});

// 5. Create a numbered list
await applyListStyle({
  docId: "document_id",
  textToFind: "Key Points",
  listType: "NUMBERED",
  indentLevel: 1
});

// 6. Insert page break
await insertPageBreak({
  docId: "document_id",
  index: 200
});
```

### Using Smart Prompts

```typescript
// Create a document using the intelligent prompt
await createDocument({
  title: "Project Proposal",
  content: "We need to develop a new mobile application for customer management",
  documentType: "proposal",
  style: "professional",
  audience: "executive team",
  includeTOC: "true"
});

// Analyze an existing document
await analyzeDoc({
  docId: "existing_document_id"
});

// Format a document with professional styling
await formatDocument({
  docId: "document_id",
  formattingStyle: "business",
  includeElements: "table of contents, headers"
});
```

## 🔒 Security

- **Credentials**: Never commit `credentials.json` or `token.json` to version control
- **OAuth Flow**: Automatic token refresh and secure credential storage
- **API Scopes**: Minimal required permissions for Google APIs
- **Error Handling**: Comprehensive error handling without exposing sensitive data

## 🐛 Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Ensure `credentials.json` exists in project root
   - Verify Google Cloud project has required APIs enabled
   - Check OAuth 2.0 client ID configuration

2. **Build Errors**:
   - Run `npm run clean && npm run build`
   - Ensure Node.js version is 18.0.0 or later
   - Check TypeScript configuration

3. **API Errors**:
   - Verify document IDs are correct
   - Check Google API quotas and limits
   - Ensure proper permissions for document operations

### Debug Mode

Enable debug logging by setting environment variable:
```bash
DEBUG=mcp-google-docs npm start
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-tool`
3. Add your changes following the modular architecture
4. Update tests and documentation
5. Submit a pull request

### Development Guidelines

- Follow the existing modular structure
- Add comprehensive TypeScript types
- Include error handling for all operations
- Update documentation for new features
- Maintain backward compatibility

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google APIs for comprehensive document manipulation capabilities
- Model Context Protocol for the integration framework
- TypeScript for type safety and developer experience
- The open-source community for inspiration and contributions

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/olpetit/gdocs-mcp/issues)
- **Documentation**: [Project Wiki](https://github.com/olpetit/gdocs-mcp/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/olpetit/gdocs-mcp/discussions)

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Maintainer**: Google Docs MCP Team