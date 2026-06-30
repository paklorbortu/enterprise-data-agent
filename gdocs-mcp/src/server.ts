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
 * Google Docs MCP Server - Main Entry Point
 * 
 * This server provides Model Context Protocol (MCP) tools for interacting with Google Docs.
 * It supports document creation, editing, formatting, and professional document features.
 * 
 * Features:
 * - Document CRUD operations (create, read, update, delete)
 * - Advanced formatting (text styles, paragraph styles, lists)
 * - Table manipulation and creation
 * - Professional features (images, TOC, headers/footers, PDF export)
 * - Content manipulation (insert, delete, page breaks)
 * 
 * @author Google Docs MCP Team
 * @version 1.0.0
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

// Import modular components
import { initApiClients, isAuthConfigured } from "./auth.js";
import { registerResources } from "./resources.js";
import { registerPrompts } from "./prompts.js";
import { registerAllTools } from "./tools/index.js";

/**
 * Main server initialization function
 */
async function main(): Promise<void> {
  try {
    console.error("Starting Google Docs MCP Server...");
    
    // Check if authentication is configured
    if (!isAuthConfigured()) {
      console.error("ERROR: Authentication not configured!");
      console.error("Please ensure credentials.json exists in the project root.");
      console.error("See README.md for setup instructions.");
      process.exit(1);
    }
    
    // Initialize Google API clients
    console.error("Initializing Google API clients...");
    const clients = await initApiClients();
    console.error("✓ Google API clients initialized successfully");
    
    // Create MCP server instance
    const server = new McpServer({
      name: "google-docs",
      version: "1.0.0",
    });
    
    // Register all server components
    console.error("Registering server components...");
    
    // Register resources (document listing and retrieval)
    registerResources(server, clients);
    console.error("✓ Resources registered");
    
    // Register prompts (pre-configured prompts for common operations)
    registerPrompts(server);
    console.error("✓ Prompts registered");
    
    // Register all tools (document manipulation, formatting, professional features)
    registerAllTools(server, clients);
    console.error("✓ All tools registered");
    
    // Create transport and connect server
    console.error("Setting up server transport...");
    const transport = new StdioServerTransport();
    await server.connect(transport);
    
    console.error("🚀 Google Docs MCP Server is running on stdio");
    console.error("Server ready to handle requests!");
    
  } catch (error) {
    console.error("❌ Fatal error during server initialization:", error);
    if (error instanceof Error) {
      console.error("Error message:", error.message);
      if (error.stack) {
        console.error("Stack trace:", error.stack);
      }
    }
    process.exit(1);
  }
}

// Handle uncaught exceptions and unhandled rejections
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Start the server
main().catch((error) => {
  console.error("Failed to start server:", error);
  process.exit(1);
});