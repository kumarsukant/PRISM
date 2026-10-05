// src/services/api.ts - Backend API communication

import { invoke } from '@tauri-apps/api/core';

import type {
  ScanStartRequest,
  ScanStartResponse,
  ScanProgressResponse,
  ScanResults,
  DeleteRequest,
  DeleteResponse,
} from '../types';

/** The backend's own explanation ({"message": "..."}) if it sent one, else the HTTP status text. */
async function errorMessage(response: Response): Promise<string> {
  const fallback = response.statusText
    ? `HTTP ${response.status}: ${response.statusText}`
    : `HTTP ${response.status}`;
  try {
    const data: unknown = await response.json();
    if (data && typeof data === 'object' && 'message' in data) {
      const message = (data as { message: unknown }).message;
      if (typeof message === 'string' && message.trim()) return message.trim();
    }
  } catch {
    // body was empty or not JSON
  }
  return fallback;
}

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

    let response: Response;
    try {
      response = await fetch(url, options);
    } catch (error) {
      // fetch only throws when there is no HTTP response at all (backend stopped or crashed)
      console.error(`API Error [${method} ${endpoint}]:`, error);
      throw new Error("Prism's background service isn't responding. Close Prism and open it again.");
    }

    if (!response.ok) {
      const message = await errorMessage(response);
      console.error(`API Error [${method} ${endpoint}]: ${message}`);
      throw new Error(message);
    }

    return (await response.json()) as T;
  }

  async checkHealth(): Promise<{ status: string }> {
    return this.request('/health', 'GET');
  }

  async startScan(folderPath: string): Promise<ScanStartResponse> {
    const request: ScanStartRequest = { folder_path: folderPath };
    return this.request('/scan/start', 'POST', request);
  }

  async getScanProgress(scanId: string): Promise<ScanProgressResponse> {
    return this.request(`/scan/progress?scan_id=${scanId}`, 'GET');
  }

  /** Polls /scan/progress until the scan finishes. Tolerates a few failed polls in a row. */
  async waitForScan(
    scanId: string,
    onProgress: (progress: ScanProgressResponse) => void
  ): Promise<ScanProgressResponse> {
    let failures = 0;
    for (;;) {
      try {
        const progress = await this.getScanProgress(scanId);
        failures = 0;
        onProgress(progress);
        if (progress.status === 'completed') return progress;
        if (progress.status === 'failed' || progress.status === 'cancelled') {
          throw new Error(progress.error_message || 'The scan failed');
        }
      } catch (error) {
        failures += 1;
        if (failures >= 5) throw error;
      }
      await new Promise((resolve) => setTimeout(resolve, 400));
    }
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
