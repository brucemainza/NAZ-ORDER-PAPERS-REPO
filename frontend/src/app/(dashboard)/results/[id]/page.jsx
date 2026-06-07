"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ResultCard } from "@/components/search/ResultCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button, buttonStyles } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { Textarea } from "@/components/ui/Textarea";
import { Toast } from "@/components/ui/Toast";
import { normalizeSearchResult, normalizeSubmission } from "@/lib/records";
import { formatDate, formatDateTime } from "@/lib/utils";

export default function ResultDetailPage() {
    const params = useParams();
    const [submission, setSubmission] = useState(null);
    const [matches, setMatches] = useState([]);
    const [sessions, setSessions] = useState([]);
    const [decision, setDecision] = useState("Clear (New)");
    const [selectedMatchId, setSelectedMatchId] = useState("");
    const [notes, setNotes] = useState("");
    const [history, setHistory] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [savedDecision, setSavedDecision] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    const loadRecord = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const [recordResponse, similarResponse, reviewsResponse, sessionsResponse] = await Promise.all([
                fetch(`/api/records/${params.id}`),
                fetch(`/api/records/${params.id}/similar`),
                fetch(`/api/records/${params.id}/reviews`),
                fetch(`/api/sessions`),
            ]);
            const recordData = await recordResponse.json().catch(() => ({}));
            if (!recordResponse.ok) {
                throw new Error(recordData.message || "Record not found");
            }
            const similarData = await similarResponse.json().catch(() => []);
            const reviewsData = await reviewsResponse.json().catch(() => []);
            const sessionsData = await sessionsResponse.json().catch(() => []);
            setSessions(Array.isArray(sessionsData) ? sessionsData : []);
            setSubmission(normalizeSubmission(recordData));
            setMatches(Array.isArray(similarData) ? similarData.map(normalizeSearchResult) : []);
            setHistory(Array.isArray(reviewsData) ? reviewsData : []);
            if (Array.isArray(similarData) && similarData.length > 0) {
                setSelectedMatchId(similarData[0].record.id);
            }
        } catch (err) {
            setSubmission(null);
            setError(err.message || "Record not found");
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadRecord();
    }, [params.id]);

    const selectedMatch = useMemo(() => matches.find((item) => item.match.id === selectedMatchId), [matches, selectedMatchId]);

    const recordDecision = async () => {
        setIsSaving(true);
        setSavedDecision(false);
        try {
            const response = await fetch(`/api/records/${params.id}/reviews`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    decision,
                    similar_record_id: decision === "Clear (New)" ? null : selectedMatchId || null,
                    notes,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.message || "Could not record decision");
            }
            setHistory((current) => [data, ...current]);
            setSubmission((current) => current ? { ...current, status: data.decision } : current);
            setNotes("");
            setSavedDecision(true);
        } catch (err) {
            setError(err.message || "Could not record decision");
        } finally {
            setIsSaving(false);
        }
    };

    if (isLoading) {
        return (<div>
          <PageHeader title="Result Record" description="Detailed submission review and historical similarity context."/>
          <div className="rounded-md border border-[--border] bg-white px-6 py-10 text-center shadow-sm">
            <Spinner className="mx-auto h-6 w-6"/>
            <p className="mt-3 text-sm text-[--muted]">Loading record details...</p>
          </div>
        </div>);
    }

    if (!submission) {
        return (<div>
          <PageHeader title="Result Record" description="Detailed submission review and historical similarity context."/>
          <EmptyState title="Record not found" description={error || "The requested record could not be located."}/>
        </div>);
    }

    return (<div>
      <PageHeader title="Result Record" description="Review the submitted item, inspect ranked similarity matches and capture the clerk's decision." actions={<Link href="/search" className={buttonStyles({ variant: "secondary" })}>
            Back to Submissions
          </Link>}/>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_360px]">
        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={submission.type === "Question" ? "question" : "motion"}>{submission.type}</Badge>
              <Badge variant={submission.status === "Duplicate" ? "duplicate" : submission.status === "Clear (New)" ? "clear" : "reviewed"}>{submission.status}</Badge>
            </div>
            <h2 className="mt-4 text-xl font-semibold text-[--black]">{submission.subject}</h2>
            <div className="mt-3 flex flex-wrap gap-4 text-sm text-[--muted]">
              <span>Member: {submission.member}</span>
              <span>Date: {formatDate(submission.submittedAt)}</span>
              {submission.ministry ? <span>Ministry: {submission.ministry}</span> : null}
            </div>
            <div className="mt-5 rounded-md border border-[--border] bg-[--bg] p-4 text-sm leading-6 text-[--black]">
              {submission.fullText}
            </div>
          </Card>

          <section className="space-y-4">
            <div>
              <h2 className="text-base font-medium text-[--black]">Previously Addressed Candidates</h2>
              <p className="text-sm text-[--muted]">Ranked records found by BM25 search and pgvector similarity where embeddings are available.</p>
            </div>
            {matches.length === 0 ? (<EmptyState title="No similar records found" description="No historical candidates were returned for this record."/>) : (matches.map((result) => {
              const sessionName = sessions.find(s => s.id === result.match.sessionId)?.name || result.match.sessionId;
              return <ResultCard key={result.match.id} result={{...result, match: {...result.match, sessionName}}} expandable initiallyExpanded={result.rank === 1}/>
            }))}
          </section>

          <section className="space-y-4">
            <div>
              <h2 className="text-base font-medium text-[--black]">Review History</h2>
              <p className="text-sm text-[--muted]">Recorded decisions for this record.</p>
            </div>

            <Card className="divide-y divide-[--border]">
              {history.length === 0 ? (<div className="px-5 py-6 text-sm text-[--muted]">No decisions have been recorded yet.</div>) : history.map((entry) => (<div key={entry.id} className="px-5 py-4">
                    <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                      <div>
                        <p className="font-medium text-[--black]">{entry.decision}</p>
                        <p className="mt-1 text-sm text-[--muted]">{entry.notes || "No decision notes captured."}</p>
                      </div>
                      <p className="text-xs text-[--muted]">{entry.reviewer_name || "Reviewer"} • {formatDateTime(entry.created_at)}</p>
                    </div>
                  </div>))}
            </Card>
          </section>
        </div>

        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="text-base font-medium text-[--black]">Clerk Decision Panel</h2>
            <p className="mt-1 text-sm text-[--muted]">Record the review outcome and connect it to the closest historical record when relevant.</p>

            <fieldset className="mt-5 space-y-3">
              <legend className="text-sm font-medium text-[--black]">Decision</legend>
              {["Clear (New)", "Duplicate", "Substantially Similar"].map((option) => (<label key={option} className="flex items-center gap-2 rounded-md border border-[--border] bg-[--bg] px-3 py-2 text-sm">
                  <input type="radio" name="decision" className="h-4 w-4 accent-[--primary]" checked={decision === option} onChange={() => setDecision(option)}/>
                  <span>{option}</span>
                </label>))}
            </fieldset>

            {decision !== "Clear (New)" ? (<div className="mt-4">
              <label className="mb-2 block text-sm font-medium text-[--black]">Related historical record</label>
              <select className="w-full rounded-md border border-[--border] bg-white px-3 py-2 text-sm" value={selectedMatchId} onChange={(event) => setSelectedMatchId(event.target.value)}>
                <option value="">Select a candidate</option>
                {matches.map((result) => (<option key={result.match.id} value={result.match.id}>
                  #{result.rank} {result.match.title}
                </option>))}
              </select>
              {selectedMatch ? <p className="mt-2 text-xs text-[--muted]">Selected similarity: {selectedMatch.match.score}%</p> : null}
            </div>) : null}

            <div className="mt-4">
              <Textarea label="Clerk Notes" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Add reasoning, context or follow-up guidance."/>
            </div>

            {savedDecision ? (<div className="mt-4">
                <Toast variant="success" title="Decision recorded" description="The review decision was saved to the database."/>
              </div>) : null}
            {error ? (<div className="mt-4">
                <Toast variant="error" title="Review error" description={error}/>
              </div>) : null}

            <div className="mt-4">
              <Button fullWidth onClick={recordDecision} disabled={isSaving || (decision !== "Clear (New)" && !selectedMatchId)}>
                {isSaving ? "Saving..." : "Record Decision"}
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>);
}
