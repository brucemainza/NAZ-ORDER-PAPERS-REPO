import { cn } from "@/lib/utils";
export function SimilarityScore({ score }) {
    const tone = score > 80 ? "bg-[--success]" : score >= 50 ? "bg-amber-500" : "bg-[--danger]";
    return (<div className="space-y-1">
      <div className="flex items-center justify-between text-xs font-medium text-[--muted]">
        <span>Similarity</span>
        <span className="text-[--black]">{score}%</span>
      </div>
      <div className="h-2 rounded bg-[--bg]">
        <div className={cn("h-2 rounded", tone)} style={{ width: `${score}%` }}/>
      </div>
    </div>);
}
