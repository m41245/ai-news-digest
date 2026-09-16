import { Badge } from "./ui/Badge";

interface ProvenanceBadgeProps {
  provenanceSource?: string | null;
  aiProvider?: string | null;
  aiModel?: string | null;
  aiProcessedAt?: string | null;
  extractionQuality?: string | null;
  showDetails?: boolean;
}

export function ProvenanceBadge({
  provenanceSource,
  aiProvider,
  aiModel,
  aiProcessedAt,
  extractionQuality,
  showDetails = false,
}: ProvenanceBadgeProps) {
  const isAi = provenanceSource === "ai_extracted";
  const isDeterministic = provenanceSource === "deterministic";

  if (!provenanceSource && !aiProvider && !extractionQuality) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {isAi && (
        <Badge tone="brand">AI-derived</Badge>
      )}
      {isDeterministic && (
        <Badge tone="neutral">Deterministic</Badge>
      )}
      {extractionQuality && (
        <Badge tone="neutral">{extractionQuality}</Badge>
      )}
      {showDetails && isAi && aiProvider && (
        <span className="text-xs text-slate-500">
          {aiProvider}{aiModel ? ` / ${aiModel}` : ""}
        </span>
      )}
      {showDetails && aiProcessedAt && (
        <span className="text-xs text-slate-400">
          Processed: {new Date(aiProcessedAt).toLocaleDateString()}
        </span>
      )}
    </div>
  );
}
