"use client";
import Link from "next/link";
import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button, buttonStyles } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { formatDate } from "@/lib/utils";

export function SubmissionCard({ record }) {
    const [isExpanded, setIsExpanded] = useState(false);
    
    const fullText = record.full_text || '';
    const hasLongText = fullText.length > 220 || fullText.split('\n').length > 2;
    const displayText = fullText;
    const shouldShowExpandButton = hasLongText;
    
    return (<Card className="p-5">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-3 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={record.item_type === "Question" ? "question" : "motion"}>{record.item_type}</Badge>
            <Badge variant={record.status === "Duplicate" ? "duplicate" : record.status === "Pending Review" ? "pending" : "clear"}>{record.status}</Badge>
            {record.session_name ? <Badge variant="info">{record.session_name}</Badge> : null}
          </div>
          <div>
            <h3 className="text-base font-medium text-[--black]">{record.subject}</h3>
            <p className="mt-1 text-sm text-[--muted]">
              {record.member} {record.ministry ? `• ${record.ministry}` : ""} • {formatDate(record.created_at)}
            </p>
          </div>
          {fullText && (
            <>
              <p className={isExpanded ? "text-sm text-[--black] whitespace-pre-line" : "text-sm text-[--black] whitespace-pre-line line-clamp-2 overflow-hidden"}>
                {displayText}
              </p>
              {shouldShowExpandButton && (
                <Button variant="ghost" size="sm" onClick={() => setIsExpanded(!isExpanded)} className="mt-2">
                  {isExpanded ? <ChevronUp className="h-4 w-4 mr-1" /> : <ChevronDown className="h-4 w-4 mr-1" />}
                  {isExpanded ? "Collapse" : "Expand"}
                </Button>
              )}
            </>
          )}
        </div>

        <div className="flex flex-col items-start gap-3 sm:items-end">
          <Link href={`/results/${record.id}`} className={buttonStyles({ variant: "secondary", size: "sm" })}>
            View Full Record
          </Link>
        </div>
      </div>
    </Card>);
}
