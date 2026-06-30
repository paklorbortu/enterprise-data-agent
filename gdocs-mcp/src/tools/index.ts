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
 * Tools index - exports all tool registration functions
 * Centralized module for registering all Google Docs MCP tools
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { ApiClients } from "../types.js";

// Import all tool registration functions
import { registerBasicTools } from "./basic-tools.js";
import { registerFormattingTools } from "./formatting-tools.js";
import { registerContentTools } from "./content-tools.js";

/**
 * Register all tools with the MCP server
 * This function should be called during server initialization
 */
export function registerAllTools(server: McpServer, clients: ApiClients): void {
  console.error("Registering all Google Docs MCP tools...");
  
  // Register basic document manipulation tools
  registerBasicTools(server, clients);
  console.error("✓ Basic tools registered");
  
  // Register formatting tools
  registerFormattingTools(server, clients);
  console.error("✓ Formatting tools registered");
  
  
  // Register content manipulation tools
  registerContentTools(server, clients);
  console.error("✓ Content tools registered");
  
  console.error("All tools registered successfully!");
}

// Export individual tool registration functions for selective registration
export {
  registerBasicTools,
  registerFormattingTools,
  registerContentTools,
};
