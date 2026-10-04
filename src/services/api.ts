// src/services/api.ts - Backend API communication

import { invoke } from '@tauri-apps/api/core';

import type {
  ScanStartRequest,
  ScanStartResponse,
  ScanResults,
  DeleteRequest,
  DeleteResponse,
} from '../types';

class ApiService {
  private baseUrl = 'http://127.0.0.1:8000';

  /** Resolves the backend port (dynamic in the installed app), then waits until /health answers. */
  async waitForBackend(timeoutMs = 30000): Promise<void> {
    try {
      const port = await invoke<number>('backend_port');
      this.baseUrl = `http://127.0.0.1:${port}`;
    } catch {
      // Not running inside Tauri (plain browser dev): keep the default port 8000.
    }

    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      try {
        const response = await fetch(`${this.baseUrl}/health`);
        if (response.ok) return;
      } catch {
        // backend not up yet
      }
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
    throw new Error(
      'Prism could not start its background service. Details are in backend.log in %LOCALAPPDATA%\\com.kumarsukant.prism'
    );
  }

  thumbnailUrl(path: string): string {
    return `${this.baseUrl}/thumbnail?path=${encodeURIComponent(path)}`;
  }

  private async request<T>(
    endpoint: string,
    method: 'GET' | 'POST' = 'GET',
    body?: object
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    try {
      const response = await fetch(url, options);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return (await response.json()) as T;
    } catch (error) {
      console.error(`API Error [${method} ${endpoint}]:`, error);
      throw error;
    }
  }

  async checkHealth(): Promise<{ status: string }> {
    return this.request('/health', 'GET');
  }

  async startScan(folderPath: string): Promise<ScanStartResponse> {
    const request: ScanStartRequest = { folder_path: folderPath };
    return this.request('/scan/start', 'POST', request);
  }

  async getScanProgress(scanId: string): Promise<any> {
    return this.request(`/scan/progress?scan_id=${scanId}`, 'GET');
  }

  async getScanResults(scanId: string): Promise<ScanResults> {
    return this.request(`/scan/results?scan_id=${scanId}`, 'GET');
  }

  async deleteDuplicates(scanId: string, groupIds: string[]): Promise<DeleteResponse> {
    const request: DeleteRequest = { scan_id: scanId, group_ids: groupIds };
    return this.request('/scan/delete', 'POST', request);
  }

  async getStats(): Promise<any> {
    return this.request('/stats', 'GET');
  }
}

export const api = new ApiService();
