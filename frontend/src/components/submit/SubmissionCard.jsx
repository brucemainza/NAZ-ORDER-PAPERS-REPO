"use client";
import Link from "next/link";
import { useState } from "react";
import { ArrowRight, ChevronDown, ChevronUp } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button, buttonStyles } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { formatDate } from "@/lib/utils";

const statusVariantMap = {
    Draft: "info",
    Submitted: "info",
    "Under Review": "pending",
    Approved: "clear",
    Rejected: "duplicate",
    Scheduled: "reviewed",
    Archived: "reviewed",
};

export function SubmissionCard({ record }) {
    const [isExpanded, setIsExpanded] = useState(false);
    
    const fullText = record.full_text || '';
    const hasLongText = fullText.length > 220 || fullText.split('\n').length > 2;
    const displayText = fullText;
    const shouldShowExpandButton = hasLongText;
    
    return (<Card className="submission-card">
      <div className="submission-card__layout">
        <div className="submission-card__main">
          <div>
            <p className="submission-card__reference">SUB-{String(record.id).slice(0, 8).toUpperCase()}</p>
            <h3 className="submission-card__title">{record.subject}</h3>
            <p className="submission-card__meta">
              Submitted by {record.member} {record.ministry ? `• ${record.ministry}` : ""} • {formatDate(record.created_at)}
            </p>
          </div>
          <div className="submission-card__badges">
            <Badge variant={record.item_type === "Question" ? "question" : "motion"}>{record.item_type}</Badge>
            {record.answer_type ? <Badge variant="info">{record.answer_type} answer</Badge> : null}
            <Badge variant={statusVariantMap[record.status] || "info"}>{record.status}</Badge>
            {record.session_name ? <Badge variant="info">{record.session_name}</Badge> : null}
            {typeof record.search_score === "number" ? <Badge variant="clear">{record.search_score}% relevance</Badge> : null}
          </div>
          {fullText && (
            <>
              {record.matched_terms?.length ? (
                <p className="submission-card__match">
                  Matched content: {record.matched_terms.join(", ")}
                </p>
              ) : null}
              <p className={isExpanded ? "submission-card__text" : "submission-card__text submission-card__text--collapsed"}>
                {displayText}
              </p>
              {shouldShowExpandButton && (
                <Button variant="ghost" size="sm" onClick={() => setIsExpanded(!isExpanded)} className="submission-card__expand">
                  {isExpanded ? <ChevronUp className="submission-card__icon" /> : <ChevronDown className="submission-card__icon" />}
                  {isExpanded ? "Collapse" : "Expand"}
                </Button>
              )}
            </>
          )}
        </div>

        <div className="submission-card__actions">
          <Link href={`/results/${record.id}`} className={buttonStyles({ variant: "ghost", size: "sm" })}>
            View Full Record <ArrowRight className="submission-card__action-icon" />
          </Link>
        </div>
      </div>
    </Card>);
}
