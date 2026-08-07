export type ScanStatus = "NOT_SCANNED" | "SCANNING" | "READY" | "FAILED";

export interface Project {
  id: string;
  name: string;
  rootPath: string;
  language: string;
  framework: string;
  scanStatus: ScanStatus;
  activeRevisionId: string | null;
  totalFiles: number;
  totalEndpoints: number;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectCreate {
  name: string;
  rootPath: string;
}

export interface PaginationMeta {
  page: number;
  pageSize: number;
  total: number;
}

