import { Badge } from "./ui/Badge";

interface IntelligenceQualityPanelProps {
  qualityFlags?: string[];
  qualityExplanation?: string;
  overallQualityScore?: number;
  provenanceComplete?: boolean;
  className?: string;
}

export function IntelligenceQualityPanel({
  qualityFlags = [],
  qualityExplanation,
  overallQualityScore,
  provenanceComplete,
  className = "",
}: IntelligenceQualityPanelProps) {
  if (!qualityFlags.length && !qualityExplanation && overallQualityScore === undefined) {
    return null;
  }

  const flagLabels: Record<string, { label: string; tone: "danger" | "warning" | "brand" | "neutral" }> = {
    missing_evidence: { label: "Missing evidence", tone: "danger" },
    low_source_diversity: { label: "Low source diversity", tone: "warning" },
    conflicting_evidence: { label: "Conflicting evidence", tone: "warning" },
    stale_intelligence: { label: "Stale intelligence", tone: "neutral" },
    ai_metadata_missing: { label: "AI metadata incomplete", tone: "warning" },
    incomplete_provenance: { label: "Incomplete provenance", tone: "warning" },
    unverified_claim: { label: "Unverified claim", tone: "warning" },
    single_source: { label: "Single source", tone: "neutral" },
    low_confidence: { label: "Low confidence", tone: "warning" },
    high_conflict: { label: "High conflict", tone: "danger" },
  };

  return (
    <div className={`rounded-xl border border-slate-200 bg-slate-50 p-4 ${className}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-slate-700">Quality Assessment</span>
        {overallQualityScore !== undefined && (
          <span className="text-xs text-slate-500">
            Score: {(overallQualityScore * 100).toFixed(0)}%
          </span>
        )}
        {provenanceComplete !== undefined && (
          <Badge tone={provenanceComplete ? "brand" : "warning"}>
            {provenanceComplete ? "Complete provenance" : "Incomplete provenance"}
          </Badge>
        )}
      </div>
      {qualityExplanation && (
        <p className="mt-1 text-xs text-slate-600">{qualityExplanation}</p>
      )}
      {qualityFlags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {qualityFlags.map((flag) => {
            const config = flagLabels[flag] || { label: flag, tone: "neutral" as const };
            return (
              <Badge key={flag} tone={config.tone}>
                {config.label}
              </Badge>
            );
          })}
        </div>
      )}
    </div>
  );
}
