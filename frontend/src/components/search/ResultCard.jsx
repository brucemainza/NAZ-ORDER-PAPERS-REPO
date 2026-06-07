"use client";
import { ChevronDown, ChevronUp, FileSearch } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { SimilarityScore } from "@/components/shared/SimilarityScore";
import { SessionBadge } from "@/components/shared/SessionBadge";
import { Badge } from "@/components/ui/Badge";
import { Button, buttonStyles } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { formatDate } from "@/lib/utils";
export function ResultCard({ result, expandable = false, initiallyExpanded = false, }) {
    const [isExpanded, setIsExpanded] = useState(initiallyExpanded);
    const sessionLabel = result.match.sessionName || result.match.sessionId;
    const fullText = result.match.fullText || result.match.snippet || "";
    const contentClassName = isExpanded ? "text-sm text-[--black] whitespace-pre-line" : "text-sm text-[--black] line-clamp-2 overflow-hidden";
    const shouldShowExpandButton = fullText.length > 220;
    return (<Card className="p-5">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="info">Rank #{result.rank}</Badge>
            <Badge variant={result.match.itemType === "Question" ? "question" : "motion"}>{result.match.itemType}</Badge>
            {sessionLabel ? <SessionBadge label={sessionLabel}/> : null}
          </div>
          <div>
            <h3 className="text-base font-medium text-[--black]">{result.match.title}</h3>
            <p className="mt-1 text-sm text-[--muted]">
              {result.match.member} {result.match.ministry ? `• ${result.match.ministry}` : ""} • {formatDate(result.match.date)}
            </p>
          </div>
          <p className={contentClassName}>{fullText}</p>
        </div>

        <div className="w-full max-w-xs space-y-3">
          <SimilarityScore score={result.match.score}/>
          <div className="flex flex-wrap gap-2">
            <Link href={`/results/${result.match.id}`} className={buttonStyles({ variant: "secondary", size: "sm" })}>
              <FileSearch className="h-4 w-4"/>
              View Full Record
            </Link>
            {expandable ? (<Button variant="ghost" size="sm" onClick={() => setIsExpanded((value) => !value)}>
                {isExpanded ? <ChevronUp className="h-4 w-4"/> : <ChevronDown className="h-4 w-4"/>}
                {isExpanded ? "Collapse" : "Expand"}
              </Button>) : null}
          </div>
        </div>
      </div>
    </Card>);
}
