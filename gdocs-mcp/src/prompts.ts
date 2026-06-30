/**
 * Copyright (C) 2025 Red Hat, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

/**
 * Prompt definitions for Google Docs MCP Server
 * Provides pre-configured prompts for common document operations
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

/**
 * Register prompt handlers with the MCP server
 */
export function registerPrompts(server: McpServer): void {
  // Unified prompt for document creation
  server.prompt(
    "create-document",
    { 
      title: z.string().describe("The title for the new document"),
      content: z.string().describe("The content for the document (can be subject, key points, or full content)"),
      documentType: z.string().optional().describe("Type of document (report, letter, memo, proposal, presentation, manual, etc.)"),
      style: z.string().optional().describe("The writing style (e.g., formal, casual, academic, professional)"),
      audience: z.string().optional().describe("Target audience for the document"),
      includeTOC: z.string().optional().describe("Whether to include a table of contents (true/false, default: false)"),
    },
    ({ title, content, documentType = "document", style = "professional", audience, includeTOC = "false" }) => ({
      messages: [{
        role: "user",
        content: {
          type: "text",
          text: `Create a ${documentType} titled "${title}" with the following content: ${content}${audience ? ` for ${audience}` : ''} in a ${style} writing style.

CRITICAL DOCUMENT MANAGEMENT RULES:
1. Create the document ONCE with ALL content included
2. NEVER create multiple documents for the same content
3. NEVER delete and recreate documents
4. Use insert-text-at-index to add content to existing documents
5. Use update-doc only when you know the exact insertion point
6. If content insertion fails, try insert-text-at-index instead of recreating
7. Plan the complete document structure before creating

MANDATORY FORMATTING REQUIREMENTS:
- NEVER include markdown syntax in the document content
- Write all text in plain format without any markdown characters
- After creating the document, immediately apply Google Docs formatting:
  * Use apply-paragraph-style for headings (TITLE, HEADING_1, HEADING_2, etc.)
  * Use apply-text-style for bold, italic, and other text formatting
  * Use apply-list-style for bullet points and numbered lists
- Clean up any markdown artifacts that might appear
- Ensure the final document uses only Google Docs native formatting
- NOTE: Tables will be handled manually in the final document

EFFICIENCY GOAL: Create one document, add all content, apply formatting - NO multiple iterations!`
        }
      }]
    })
  );

  // Prompt for document analysis
  server.prompt(
    "analyze-doc",
    { 
      docId: z.string().describe("The ID of the document to analyze"),
    },
    ({ docId }) => ({
      messages: [{
        role: "user",
        content: {
          type: "text",
          text: `Please analyze the content of the document with ID ${docId}. Provide a summary of its content, structure, key points, and any suggestions for improvement.`
        }
      }]
    })
  );

  // Prompt for document formatting
  server.prompt(
    "format-document",
    { 
      docId: z.string().describe("The ID of the document to format"),
      formattingStyle: z.string().describe("The formatting style to apply (academic, business, creative, technical)"),
      includeElements: z.string().optional().describe("Specific elements to include (e.g., 'table of contents, headers, footers')"),
    },
    ({ docId, formattingStyle, includeElements = "" }) => ({
      messages: [{
        role: "user",
        content: {
          type: "text",
          text: `Please format the document with ID ${docId} using ${formattingStyle} style. ${includeElements ? `Include these elements: ${includeElements}.` : ''} 

FORMATTING GUIDELINES:
- Remove any markdown syntax that may exist in the document
- Apply professional formatting using Google Docs native tools only
- Use proper heading styles (HEADING_1, HEADING_2, etc.) instead of markdown headers
- Apply text formatting (bold, italic) using Google Docs text styling tools
- Create lists using Google Docs native bullet points and numbering
- Ensure consistent styling throughout the document`
        }
      }]
    })
  );
}
