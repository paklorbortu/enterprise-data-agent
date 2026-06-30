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
 * Authentication module for Google Docs MCP Server
 * Handles OAuth2.0 authentication and API client initialization
 */

import { google } from "googleapis";
import { authenticate } from "@google-cloud/local-auth";
import { OAuth2Client } from "google-auth-library";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from 'url';
import { SCOPES, AuthConfig, ApiClients } from "./types.js";

// Resolve paths relative to the project root
const PROJECT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

// Default authentication configuration
const defaultAuthConfig: AuthConfig = {
  tokenPath: process.env.GDOCS_TOKEN_PATH || path.join(PROJECT_ROOT, "token.json"),
  credentialsPath: process.env.GDOCS_CREDENTIALS_PATH || path.join(PROJECT_ROOT, "credentials.json"),
  scopes: SCOPES,
};

/**
 * Load saved credentials if they exist, otherwise trigger the OAuth flow
 */
export async function authorize(config: AuthConfig = defaultAuthConfig): Promise<OAuth2Client> {
  try {
    // Load client secrets from a local file
    console.error("Reading credentials from:", config.credentialsPath);
    const content = fs.readFileSync(config.credentialsPath, "utf-8");
    const keys = JSON.parse(content);
    const clientId = keys.installed.client_id;
    const clientSecret = keys.installed.client_secret;
    const redirectUri = keys.installed.redirect_uris[0];

    console.error("Using client ID:", clientId);
    console.error("Using redirect URI:", redirectUri);

    // Create an OAuth2 client
    const oAuth2Client = new OAuth2Client(clientId, clientSecret, redirectUri);

    // Check if we have previously stored a token
    if (fs.existsSync(config.tokenPath)) {
      console.error("Found existing token, attempting to use it...");
      const token = JSON.parse(fs.readFileSync(config.tokenPath, "utf-8"));
      oAuth2Client.setCredentials(token);
      oAuth2Client.on('tokens', (tokens) => {
        try {
          const existing = fs.existsSync(config.tokenPath)
            ? JSON.parse(fs.readFileSync(config.tokenPath, "utf-8"))
            : {};
          fs.writeFileSync(config.tokenPath, JSON.stringify({ ...existing, ...tokens }));
          console.error("Token refreshed and saved to:", config.tokenPath);
        } catch (e) {
          console.error("Warning: could not write refreshed token:", e);
        }
      });
      return oAuth2Client;
    }

    // No token found, use the local-auth library to get one
    console.error("No token found, starting OAuth flow...");
    const client = await authenticate({
      scopes: config.scopes,
      keyfilePath: config.credentialsPath,
    });

    if (client.credentials) {
      console.error("Authentication successful, saving token...");
      fs.writeFileSync(config.tokenPath, JSON.stringify(client.credentials));
      console.error("Token saved successfully to:", config.tokenPath);
    } else {
      console.error("Authentication succeeded but no credentials returned");
    }

    return client;
  } catch (err) {
    console.error("Error authorizing with Google:", err);
    if (err instanceof Error) {
      console.error("Error message:", err.message);
      if (err.stack) console.error("Stack trace:", err.stack);
    }
    throw err;
  }
}

/**
 * Initialize Google API clients with authentication
 */
export async function initApiClients(config: AuthConfig = defaultAuthConfig): Promise<ApiClients> {
  try {
    console.error("Starting client initialization...");
    const auth = await authorize(config);
    console.error("Auth completed successfully:", !!auth);

    const docsClient = google.docs({ version: "v1", auth: auth as any });
    console.error("Docs client created:", !!docsClient);

    const driveClient = google.drive({ version: "v3", auth: auth as any });
    console.error("Drive client created:", !!driveClient);

    return { docsClient, driveClient };
  } catch (error) {
    console.error("Failed to initialize Google API clients:", error);
    throw error;
  }
}

/**
 * Check if authentication is properly configured
 */
export function isAuthConfigured(config: AuthConfig = defaultAuthConfig): boolean {
  return fs.existsSync(config.credentialsPath);
}

/**
 * Get authentication configuration
 */
export function getAuthConfig(): AuthConfig {
  return defaultAuthConfig;
}
