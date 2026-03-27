export type GateDecision = 'passed' | 'risk' | 'failed'

export interface GateSummary {
  transportStatus: GateDecision | 'failed'
  semanticStatus: GateDecision
  importabilityStatus: GateDecision
  semanticGateReasons?: string[]
  riskOverrideReasons?: string[]
  semanticAcceptanceReason?: string[]
}
