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
    const contentClassName = isExpanded ? "result-card__text" : "result-card__text result-card__text--collapsed";
    const shouldShowExpandButton = fullText.length > 220;
    return (<Card className="result-card">
      <div className="result-card__layout">
        <div className="result-card__main">
          <div className="result-card__badges">
            <Badge variant="info">Rank #{result.rank}</Badge>
            <Badge variant={result.match.itemType === "Question" ? "question" : "motion"}>{result.match.itemType}</Badge>
            {sessionLabel ? <SessionBadge label={sessionLabel}/> : null}
          </div>
          <div>
            <h3 className="result-card__title">{result.match.title}</h3>
            <p className="result-card__meta">
              {result.match.member} {result.match.ministry ? `• ${result.match.ministry}` : ""} • {formatDate(result.match.date)}
            </p>
          </div>
          <p className={contentClassName}>{fullText}</p>
        </div>

        <div className="result-card__aside">
          <SimilarityScore score={result.match.score}/>
          <div className="result-card__actions">
            <Link href={`/results/${result.match.id}`} className={buttonStyles({ variant: "secondary", size: "sm" })}>
              <FileSearch className="result-card__icon"/>
              View Full Record
            </Link>
            {expandable ? (<Button variant="ghost" size="sm" onClick={() => setIsExpanded((value) => !value)}>
                {isExpanded ? <ChevronUp className="result-card__icon"/> : <ChevronDown className="result-card__icon"/>}
                {isExpanded ? "Collapse" : "Expand"}
              </Button>) : null}
          </div>
        </div>
      </div>
    </Card>);
}
