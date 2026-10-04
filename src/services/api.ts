// src/services/api.ts - Backend API communication

import type {
  ScanStartRequest,
  ScanStartResponse,
  ScanResults,
  DeleteRequest,
  DeleteResponse,
} from '../types';

const API_BASE_URL = 'http://127.0.0.1:8000';

class ApiService {
  private async request<T>(
    endpoint: string,
    method: 'GET' | 'POST' = 'GET',
    body?: object
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;

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
