export type HttpMethod =
  "GET" | "POST" | "PUT" | "DELETE" | "PATCH" | "OPTIONS" | "HEAD";

export interface EndpointParameter {
  name: string;
  location:
    | "PATH"
    | "QUERY"
    | "BODY"
    | "HEADER"
    | "COOKIE"
    | "FORM"
    | "FILE"
    | "DEPENDENCY"
    | "UNKNOWN";
  type: string | null;
  required: boolean;
  default: unknown;
}

export interface EndpointDependency {
  parameterName: string | null;
  providerExpression: string | null;
  resolvedQualifiedName: string | null;
  confidence: "CONFIRMED" | "HIGH" | "MEDIUM" | "LOW";
}

export interface Endpoint {
  id: string;
  projectId: string;
  scanRevisionId: string;
  httpMethod: HttpMethod;
  path: string;
  functionName: string;
  qualifiedName: string;
  moduleName: string;
  filePath: string;
  startLine: number;
  endLine: number;
  summary: string | null;
  tags: string[];
  parameters: EndpointParameter[];
  responseType: string | null;
  dependencies: EndpointDependency[];
  metadata: Record<string, unknown>;
  createdAt: string;
}

export interface EndpointFilters {
  search: string;
  httpMethod: HttpMethod | "ALL";
  module: string;
}
