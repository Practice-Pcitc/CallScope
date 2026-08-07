export type AIConfidence = "HIGH" | "MEDIUM" | "LOW";
export type AIClaimType = "FACT" | "INFERENCE" | "UNKNOWN";

export interface AnalysisBinding {
  nodeIds: string[];
  edgeIds: string[];
  endpointIds: string[];
  evidenceIds: string[];
  filePath: string | null;
  lineNumber: number | null;
  confidence: AIConfidence;
  claimType: AIClaimType;
}

export interface ExecutionStep extends AnalysisBinding {
  step: number;
  description: string;
}

export interface KeyNode extends AnalysisBinding {
  name: string;
  reason: string;
  importance: AIConfidence;
}

export interface ConditionItem extends AnalysisBinding {
  condition: string;
  result: string;
  conditionType: string;
  evidence: string | null;
}

export interface DataFlowItem extends AnalysisBinding {
  source: string;
  transformations: string[];
  destination: string;
  result: string;
}

export interface DatabaseOperation extends AnalysisBinding {
  resource: string;
  operation: string;
  reason: string;
  repositoryMethod: string | null;
}

export interface ExceptionItem extends AnalysisBinding {
  exception: string;
  trigger: string;
  impact: string;
}

export interface ExternalDependency extends AnalysisBinding {
  dependencyType: string;
  name: string;
  purpose: string;
}

export interface RelatedEndpoint extends AnalysisBinding {
  endpointId: string;
  relation: string;
  reason: string;
}

export interface RiskItem extends AnalysisBinding {
  riskType: string;
  level: AIConfidence;
  description: string;
  label: "Potential Risk";
}

export interface ImpactItem extends AnalysisBinding {
  target: string;
  impactType: string;
  description: string;
}

export interface InferenceItem extends AnalysisBinding {
  description: string;
  basis: string;
}

export interface EvidenceItem {
  evidenceId: string;
  description: string;
  nodeId: string | null;
  edgeId: string | null;
  filePath: string | null;
  startLine: number | null;
  endLine: number | null;
}

export interface BusinessFlowStep {
  step: number;
  title: string;
  description: string;
  businessMeaning: string;
  nodeIds: string[];
}

export interface BusinessRule {
  rule: string;
  reason: string;
  failureResult: string;
  nodeIds: string[];
}

export interface StateChange {
  businessObject: string;
  before: string;
  after: string;
  nodeIds: string[];
}

export interface BusinessDataFlow {
  inputs: string[];
  reads: string[];
  changes: string[];
  outputs: string[];
}

export interface FailureFlow {
  scenario: string;
  reason: string;
  businessImpact: string;
  nodeIds: string[];
}

export interface CoreBusinessObject {
  name: string;
  role: string;
}

export interface KeyBusinessNode {
  name: string;
  businessImportance: string;
  reason: string;
  nodeIds: string[];
}

export interface ProcessPosition {
  position: "START" | "MIDDLE" | "END" | "INDEPENDENT" | "UNKNOWN";
  description: string;
}

export interface BusinessRelatedEndpoint {
  endpointId: string;
  relationship: string;
  businessReason: string;
}

export interface BusinessRisk {
  title: string;
  description: string;
  level: AIConfidence;
  nodeIds: string[];
}

export interface TechnicalReference {
  entry: string;
  coreMethods: string[];
  dataAccess: string[];
  sourceFiles: string[];
}

export interface AIChainAnalysis {
  businessSummary: string;
  businessScenario: string;
  businessFlow: BusinessFlowStep[];
  businessRules: BusinessRule[];
  stateChanges: StateChange[];
  businessDataFlow: BusinessDataFlow;
  normalFlow: string[];
  failureFlows: FailureFlow[];
  coreBusinessObjects: CoreBusinessObject[];
  keyBusinessNodes: KeyBusinessNode[];
  processPosition: ProcessPosition;
  relatedEndpoints: BusinessRelatedEndpoint[];
  businessRisks: BusinessRisk[];
  technicalReference: TechnicalReference;
}

export interface AIAnalysisData {
  analysisId: string;
  projectId: string;
  scanRevisionId: string;
  scopeType: string;
  status: "ANALYZING" | "COMPLETED" | "FAILED" | "STALE";
  provider: string;
  model: string;
  cached: boolean;
  stale: boolean;
  result: AIChainAnalysis | null;
  errorMessage: string | null;
  tokenUsage: Record<string, unknown>;
  invalidReferenceCount: number;
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
}

export interface AnalysisRequest {
  depth?: number;
  includeSource?: boolean;
  includeMediumConfidence?: boolean;
  forceRegenerate?: boolean;
}
