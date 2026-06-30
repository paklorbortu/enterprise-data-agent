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
 * Basic document manipulation tools
 * Handles creation, updating, searching, and deletion of documents
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { ApiClients, ToolResponse } from "../types.js";

/**
 * Register basic document tools with the MCP server
 */
export function registerBasicTools(server: McpServer, clients: ApiClients): void {
  const { docsClient, driveClient } = clients;

  // Tool to create a new document
  server.tool(
    "create-doc",
    {
      title: z.string().describe("The title of the new document"),
      content: z.string().optional().describe("Optional initial content for the document"),
    },
    async ({ title, content = "" }) => {
      try {
        // Create a new document
        const doc = await docsClient.documents.create({
          requestBody: {
            title: title,
          },
        });

        const documentId = doc.data.documentId;
        if (!documentId) {
          throw new Error("Failed to create document - no document ID returned");
        }

        // If content was provided, add it to the document
        if (content) {
          await docsClient.documents.batchUpdate({
            documentId,
            requestBody: {
              requests: [
                {
                  insertText: {
                    location: {
                      index: 1,
                    },
                    text: content,
                  },
                },
              ],
            },
          });
        }

        return {
          content: [
            {
              type: "text",
              text: `Document created successfully!\nTitle: ${title}\nDocument ID: ${documentId}\nYou can now reference this document using: googledocs://${documentId}`,
            },
          ],
        };
      } catch (error) {
        console.error("Error creating document:", error);
        return {
          content: [
            {
              type: "text",
              text: `Error creating document: ${error}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  // Tool to update an existing document
  server.tool(
    "update-doc",
    {
      docId: z.string().describe("The ID of the document to update"),
      content: z.string().describe("The content to add to the document"),
      replaceAll: z.boolean().optional().describe("Whether to replace all content (true) or append (false)"),
    },
    async ({ docId, content, replaceAll = false }) => {
      try {
        // Ensure docId is a string and not null/undefined
        if (!docId) {
          throw new Error("Document ID is required");
        }
        
        const documentId = String(docId);
        
        if (replaceAll) {
          // First, get the document to find its length
          const doc = await docsClient.documents.get({
            documentId,
          });
          
          // Calculate the document length
          let documentLength = 1; // Start at 1 (the first character position)
          if (doc.data.body && doc.data.body.content) {
            doc.data.body.content.forEach((element: any) => {
              if (element.paragraph) {
                element.paragraph.elements.forEach((paragraphElement: any) => {
                  if (paragraphElement.textRun && paragraphElement.textRun.content) {
                    documentLength += paragraphElement.textRun.content.length;
                  }
                });
              }
            });
          }
          
          // Delete all content and then insert new content
          await docsClient.documents.batchUpdate({
            documentId,
            requestBody: {
              requests: [
                {
                  deleteContentRange: {
                    range: {
                      startIndex: 1,
                      endIndex: documentLength,
                    },
                  },
                },
                {
                  insertText: {
                    location: {
                      index: 1,
                    },
                    text: content,
                  },
                },
              ],
            },
          });
        } else {
          // Append content to the end of the document
          const doc = await docsClient.documents.get({
            documentId,
          });
          
          // Calculate the document length to append at the end
          let documentLength = 1; // Start at 1 (the first character position)
          if (doc.data.body && doc.data.body.content) {
            doc.data.body.content.forEach((element: any) => {
              if (element.paragraph) {
                element.paragraph.elements.forEach((paragraphElement: any) => {
                  if (paragraphElement.textRun && paragraphElement.textRun.content) {
                    documentLength += paragraphElement.textRun.content.length;
                  }
                });
              }
            });
          }
          
          // Append content at the end
          await docsClient.documents.batchUpdate({
            documentId,
            requestBody: {
              requests: [
                {
                  insertText: {
                    location: {
                      index: documentLength,
                    },
                    text: content,
                  },
                },
              ],
            },
          });
        }
        
        return {
          content: [
            {
              type: "text",
              text: `Document updated successfully!\nDocument ID: ${docId}`,
            },
          ],
        };
      } catch (error) {
        console.error("Error updating document:", error);
        return {
          content: [
            {
              type: "text",
              text: `Error updating document: ${error}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  // Tool to search for documents
  server.tool(
    "search-docs",
    {
      query: z.string().describe("The search query to find documents"),
    },
    async ({ query }) => {
      try {
        const response = await driveClient.files.list({
          q: `mimeType='application/vnd.google-apps.document' and fullText contains '${query}'`,
          fields: "files(id, name, createdTime, modifiedTime)",
          pageSize: 10,
          supportsAllDrives: true,
          includeItemsFromAllDrives: true,
          corpora: 'allDrives',
        });
        
        // Add response logging for debugging
        console.error("Drive API Response:", JSON.stringify(response, null, 2));
        
        // Add better response validation
        if (!response || !response.data) {
          throw new Error("Invalid response from Google Drive API");
        }
        
        // Add null check and default to empty array
        const files = (response.data.files || []);
        
        let content = `Search results for "${query}":\n\n`;
        
        if (files.length === 0) {
          content += "No documents found matching your query.";
        } else {
          files.forEach((file: any) => {
            content += `Title: ${file.name}\n`;
            content += `ID: ${file.id}\n`;
            content += `Created: ${file.createdTime}\n`;
            content += `Last Modified: ${file.modifiedTime}\n\n`;
          });
        }
        
        return {
          content: [
            {
              type: "text",
              text: content,
            },
          ],
        };
      } catch (error) {
        console.error("Error searching documents:", error);
        // Include more detailed error information
        const errorMessage = error instanceof Error 
            ? `${error.message}\n${error.stack}` 
            : String(error);
            
        return {
          content: [
            {
              type: "text",
              text: `Error searching documents: ${errorMessage}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  // Tool to delete a document
  server.tool(
    "delete-doc",
    {
      docId: z.string().describe("The ID of the document to delete"),
    },
    async ({ docId }) => {
      try {
        // Get the document title first for confirmation
        const doc = await docsClient.documents.get({ documentId: docId });
        const title = doc.data.title;
        
        // Delete the document
        await driveClient.files.delete({
          fileId: docId,
        });

        return {
          content: [
            {
              type: "text",
              text: `Document "${title}" (ID: ${docId}) has been successfully deleted.`,
            },
          ],
        };
      } catch (error) {
        console.error(`Error deleting document ${docId}:`, error);
        return {
          content: [
            {
              type: "text",
              text: `Error deleting document: ${error}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  // Tool to read a document with different formats
  server.tool(
    "read-doc-advanced",
    {
      docId: z.string().describe("The ID of the document to read"),
      format: z.enum(['text', 'json', 'markdown']).optional().default('text').describe("Output format: 'text' (plain text), 'json' (raw API structure), 'markdown' (experimental conversion)"),
      maxLength: z.number().optional().describe("Maximum character limit for output. Use this to limit very large documents"),
    },
    async ({ docId, format = 'text', maxLength }) => {
      try {
        const documentId = docId.toString();
        
        const fields = format === 'json' || format === 'markdown' ? '*' : 'body(content(paragraph(elements(textRun(content)))))';
        
        const doc = await docsClient.documents.get({
          documentId,
          fields: fields,
        });

        if (format === 'json') {
          const jsonContent = JSON.stringify(doc.data, null, 2);
          if (maxLength && jsonContent.length > maxLength) {
            return {
              content: [
                {
                  type: "text",
                  text: jsonContent.substring(0, maxLength) + `\n... [JSON truncated: ${jsonContent.length} total chars]`,
                },
              ],
            };
          }
          return {
            content: [
              {
                type: "text",
                text: jsonContent,
              },
            ],
          };
        }

        if (format === 'markdown') {
          // Simple conversion to markdown
          let markdown = '';
          
          if (doc.data.body && doc.data.body.content) {
            doc.data.body.content.forEach((element: any) => {
              if (element.paragraph) {
                if (element.paragraph.paragraphStyle?.namedStyleType) {
                  const styleType = element.paragraph.paragraphStyle.namedStyleType;
                  if (styleType.startsWith('HEADING_')) {
                    const level = parseInt(styleType.replace('HEADING_', ''));
                    const hashes = '#'.repeat(Math.min(level, 6));
                    markdown += `${hashes} `;
                  } else if (styleType === 'TITLE') {
                    markdown += '# ';
                  } else if (styleType === 'SUBTITLE') {
                    markdown += '## ';
                  }
                }
                
                if (element.paragraph.elements) {
                  element.paragraph.elements.forEach((textElement: any) => {
                    if (textElement.textRun && textElement.textRun.content) {
                      let text = textElement.textRun.content;
                      
                      if (textElement.textRun.textStyle) {
                        const style = textElement.textRun.textStyle;
                        if (style.bold && style.italic) {
                          text = `***${text}***`;
                        } else if (style.bold) {
                          text = `**${text}**`;
                        } else if (style.italic) {
                          text = `*${text}*`;
                        }
                      }
                      
                      markdown += text;
                    }
                  });
                }
                markdown += '\n\n';
              }
            });
          }
          
          const markdownContent = markdown.trim();
          if (maxLength && markdownContent.length > maxLength) {
            return {
              content: [
                {
                  type: "text",
                  text: markdownContent.substring(0, maxLength) + `\n\n... [Markdown truncated: ${markdownContent.length} total chars]`,
                },
              ],
            };
          }
          
          return {
            content: [
              {
                type: "text",
                text: markdownContent,
              },
            ],
          };
        }

        // Default text format
        let textContent = '';
        if (doc.data.body && doc.data.body.content) {
          doc.data.body.content.forEach((element: any) => {
            if (element.paragraph && element.paragraph.elements) {
              element.paragraph.elements.forEach((textElement: any) => {
                if (textElement.textRun && textElement.textRun.content) {
                  textContent += textElement.textRun.content;
                }
              });
            }
          });
        }

        if (maxLength && textContent.length > maxLength) {
          return {
            content: [
              {
                type: "text",
                text: `Content (truncated to ${maxLength} chars of ${textContent.length} total):\n---\n${textContent.substring(0, maxLength)}\n\n... [Document continues for ${textContent.length - maxLength} more characters]`,
              },
            ],
          };
        }

        return {
          content: [
            {
              type: "text",
              text: `Content (${textContent.length} characters):\n---\n${textContent}`,
            },
          ],
        };
      } catch (error) {
        console.error("Error reading document:", error);
        return {
          content: [
            {
              type: "text",
              text: `Error reading document: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );
}
