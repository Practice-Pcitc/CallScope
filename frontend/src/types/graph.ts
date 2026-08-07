export type GraphNodeType =
  | "API"
  | "ROUTE_FUNCTION"
  | "FUNCTION"
  | "METHOD"
  | "CLASS"
  | "SERVICE"
  | "REPOSITORY"
  | "DATABASE_OPERATION"
  | "DATABASE_TABLE"
  | "PYDANTIC_MODEL"
  | "DEPENDENCY"
  | "REDIS"
  | "EXTERNAL_HTTP"
  | "CONFIG"
  | "UNRESOLVED";

export type Confidence = "CONFIRMED" | "HIGH" | "MEDIUM" | "LOW";

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  name: string;
  qualifiedName: string;
  moduleName: string | null;
  filePath: string | null;
  startLine: number | null;
  endLine: number | null;
  signature: string | null;
  loaded: boolean;
  expanded: boolean;
  hasChildren: boolean;
  childCount: number;
  depth: number;
  entryEndpointIds: string[];
  shared: boolean;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationType: string;
  confidence: Confidence;
  filePath: string | null;
  lineNumber: number | null;
  columnNumber: number | null;
  evidence: string | null;
  entryEndpointIds: string[];
  metadata: Record<string, unknown>;
}

export interface GraphData {
  projectId: string;
  scanRevisionId: string;
  roots: string[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  meta: {
    nodeCount: number;
    edgeCount: number;
    truncated: boolean;
  };
}

export interface NodeDetail extends GraphNode {
  sourceExcerpt: string | null;
  upstream: GraphEdge[];
  downstream: GraphEdge[];
}

export interface SourceData {
  nodeId: string;
  filePath: string | null;
  startLine: number | null;
  endLine: number | null;
  source: string | null;
}

export interface RelationDetail extends GraphEdge {
  sourceNode: GraphNode;
  targetNode: GraphNode;
}
