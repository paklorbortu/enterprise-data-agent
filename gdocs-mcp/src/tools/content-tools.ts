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
 * Content manipulation tools
 * Handles text insertion, deletion, and content range operations
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { ApiClients } from "../types.js";

/**
 * Register content manipulation tools with the MCP server
 */
export function registerContentTools(server: McpServer, clients: ApiClients): void {
  const { docsClient } = clients;

  // Tool to insert text at a specific index
  server.tool(
    "insert-text-at-index",
    {
      docId: z.string().describe("The ID of the document to insert text into"),
      textToInsert: z.string().min(1).describe("The text to insert"),
      index: z.number().int().min(1).describe("The index (1-based) where the text should be inserted"),
    },
    async ({ docId, textToInsert, index }) => {
      try {
        const documentId = docId.toString();
        
        await docsClient.documents.batchUpdate({
          documentId,
          requestBody: {
            requests: [{
              insertText: {
                location: { index },
                text: textToInsert,
              },
            }],
          },
        });

        return {
          content: [
            {
              type: "text",
              text: `Text inserted successfully at index ${index}!\nDocument ID: ${docId}\nText inserted: "${textToInsert}"`,
            },
          ],
        };
      } catch (error) {
        console.error("Error inserting text:", error);
        return {
          content: [
            {
              type: "text",
              text: `Error inserting text: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  // Tool to delete a content range
  server.tool(
    "delete-range",
    {
      docId: z.string().describe("The ID of the document to delete content from"),
      startIndex: z.number().int().min(1).describe("The starting index of the text range (inclusive, starts from 1)"),
      endIndex: z.number().int().min(1).describe("The ending index of the text range (exclusive)"),
    },
    async ({ docId, startIndex, endIndex }) => {
      try {
        if (endIndex <= startIndex) {
          throw new Error("End index must be greater than start index for deletion");
        }

        const documentId = docId.toString();
        
        await docsClient.documents.batchUpdate({
          documentId,
          requestBody: {
            requests: [{
              deleteContentRange: {
                range: { startIndex, endIndex },
              },
            }],
          },
        });

        return {
          content: [
            {
              type: "text",
              text: `Content deleted successfully!\nDocument ID: ${docId}\nRange deleted: ${startIndex}-${endIndex}`,
            },
          ],
        };
      } catch (error) {
        console.error("Error deleting range:", error);
        return {
          content: [
            {
              type: "text",
              text: `Error deleting range: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  // Tool to insert a page break
  server.tool(
    "insert-page-break",
    {
      docId: z.string().describe("The ID of the document to insert page break into"),
      index: z.number().int().min(1).describe("The index (1-based) where the page break should be inserted"),
    },
    async ({ docId, index }) => {
      try {
        const documentId = docId.toString();
        
        await docsClient.documents.batchUpdate({
          documentId,
          requestBody: {
            requests: [{
              insertPageBreak: {
                location: { index },
              },
            }],
          },
        });

        return {
          content: [
            {
              type: "text",
              text: `Page break inserted successfully at index ${index}!\nDocument ID: ${docId}`,
            },
          ],
        };
      } catch (error) {
        console.error("Error inserting page break:", error);
        return {
          content: [
            {
              type: "text",
              text: `Error inserting page break: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  // Tool to list comments from a document
  // Note: Comment API not available in current Google Docs API version
  server.tool(
    "list-comments",
    {
      docId: z.string().describe("The ID of the document to list comments from"),
    },
    async ({ docId }) => {
      try {
        return {
          content: [
            {
              type: "text",
              text: "Comment management is not available in the current Google Docs API version. This feature requires a newer API version or different authentication scope.",
            },
          ],
          isError: true,
        };
      } catch (error) {
        console.error("Error with comments:", error);
        return {
          content: [
            {
              type: "text",
              text: `Error with comments: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  // Tool to add a comment
  // Note: Comment API not available in current Google Docs API version
  server.tool(
    "add-comment",
    {
      docId: z.string().describe("The ID of the document to add comment to"),
      textToFind: z.string().describe("The exact text to anchor the comment to"),
      commentText: z.string().min(1).describe("The comment text to add"),
    },
    async ({ docId, textToFind, commentText }) => {
      try {
        return {
          content: [
            {
              type: "text",
              text: "Comment management is not available in the current Google Docs API version. This feature requires a newer API version or different authentication scope.",
            },
          ],
          isError: true,
        };
      } catch (error) {
        console.error("Error with comments:", error);
        return {
          content: [
            {
              type: "text",
              text: `Error with comments: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );
}
