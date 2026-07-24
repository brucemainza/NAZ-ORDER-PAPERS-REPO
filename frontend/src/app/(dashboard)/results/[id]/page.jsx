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
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { Textarea } from "@/components/ui/Textarea";
import { Toast } from "@/components/ui/Toast";
import { useAuthContext } from "@/context/AuthContext";
import { hasPermission } from "@/lib/auth";
import { normalizeSearchResult, normalizeSubmission } from "@/lib/records";
import { formatDate, formatDateTime } from "@/lib/utils";

const statusVariantMap = {
    Draft: "info",
    Submitted: "info",
    "Under Review": "pending",
    Approved: "clear",
    Rejected: "duplicate",
    Scheduled: "reviewed",
    Archived: "reviewed",
};

export default function ResultDetailPage() {
    const params = useParams();
    const { user } = useAuthContext();
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
    const [workflowNotes, setWorkflowNotes] = useState("");
    const [workflowResult, setWorkflowResult] = useState(null);
    const [workflowError, setWorkflowError] = useState(null);
    const [isWorkflowSaving, setIsWorkflowSaving] = useState(false);
    const [sittingDate, setSittingDate] = useState("");
    const [scheduleResult, setScheduleResult] = useState(null);
    const [scheduleError, setScheduleError] = useState(null);
    const [isScheduling, setIsScheduling] = useState(false);

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
    const workflowActions = [
        ...(hasPermission(user, "approve_motion") ? [{ action: "Approve", variant: "primary" }] : []),
        ...(hasPermission(user, "reject_submission") ? [{ action: "Reject", variant: "danger" }] : []),
        ...(hasPermission(user, "request_changes") ? [{ action: "Request Changes", variant: "secondary" }] : []),
    ];
    const isWorkflowReviewable = submission?.status === "Under Review";
    const canSchedule = hasPermission(user, "schedule_item") && submission?.status === "Approved";

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
            setNotes("");
            setSavedDecision(true);
        } catch (err) {
            setError(err.message || "Could not record decision");
        } finally {
            setIsSaving(false);
        }
    };

    const recordWorkflowAction = async (action) => {
        setIsWorkflowSaving(true);
        setWorkflowError(null);
        setWorkflowResult(null);
        try {
            const response = await fetch(`/api/submissions/${params.id}/workflow-review`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action, notes: workflowNotes || null }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.message || "Could not record workflow action");
            }
            setSubmission((current) => current ? { ...current, status: data.status } : current);
            setWorkflowNotes("");
            setWorkflowResult(data);
        } catch (err) {
            setWorkflowError(err.message || "Could not record workflow action");
        } finally {
            setIsWorkflowSaving(false);
        }
    };

    const scheduleSubmission = async () => {
        setIsScheduling(true);
        setScheduleError(null);
        try {
            const response = await fetch(`/api/submissions/${params.id}/schedule`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ sitting_date: sittingDate }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.message || "Could not schedule submission");
            }
            setSubmission((current) => current ? {
                ...current,
                status: data.status,
                sittingDate: data.sitting_date,
            } : current);
            setScheduleResult(data);
        } catch (err) {
            setScheduleError(err.message || "Could not schedule submission");
        } finally {
            setIsScheduling(false);
        }
    };

    if (isLoading) {
        return (<div>
          <PageHeader title="Result Record" description="Detailed submission review and historical similarity context."/>
          <div className="page-loading">
            <Spinner className="page-loading__spinner"/>
            <p className="page-loading__text">Loading record details...</p>
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

      <div className="result-detail__layout">
        <div className="result-detail__main">
          <Card className="result-detail__summary">
            <div className="result-detail__badges">
              <Badge variant={submission.type === "Question" ? "question" : "motion"}>{submission.type}</Badge>
              <Badge variant={statusVariantMap[submission.status] || "info"}>{submission.status}</Badge>
            </div>
            <h2 className="result-detail__subject">{submission.subject}</h2>
            <div className="result-detail__meta">
              <span>Member: {submission.member}</span>
              <span>Date: {formatDate(submission.submittedAt)}</span>
              {submission.ministry ? <span>Ministry: {submission.ministry}</span> : null}
              {submission.sittingDate ? <span>Sitting: {formatDate(submission.sittingDate)}</span> : null}
            </div>
            <div className="result-detail__body">
              {submission.fullText}
            </div>
          </Card>

          <section className="result-detail__section">
            <div>
              <h2 className="result-detail__section-title">Previously Addressed Candidates</h2>
              <p className="result-detail__section-description">Ranked records found by BM25 search and pgvector similarity where embeddings are available.</p>
            </div>
            {matches.length === 0 ? (<EmptyState title="No similar records found" description="No historical candidates were returned for this record."/>) : (matches.map((result) => {
              const sessionName = sessions.find(s => s.id === result.match.sessionId)?.name || result.match.sessionId;
              return <ResultCard key={result.match.id} result={{...result, match: {...result.match, sessionName}}} expandable initiallyExpanded={result.rank === 1}/>
            }))}
          </section>

          <section className="result-detail__section">
            <div>
              <h2 className="result-detail__section-title">Review History</h2>
              <p className="result-detail__section-description">Recorded similarity classifications for this record.</p>
            </div>

            <Card className="result-detail__history">
              {history.length === 0 ? (<div className="result-detail__history-empty">No decisions have been recorded yet.</div>) : history.map((entry) => (<div key={entry.id} className="result-detail__history-entry">
                    <div className="result-detail__history-row">
                      <div>
                        <p className="result-detail__history-decision">{entry.decision}</p>
                        <p className="result-detail__history-notes">{entry.notes || "No decision notes captured."}</p>
                      </div>
                      <p className="result-detail__history-date">{entry.reviewer_name || "Reviewer"} • {formatDateTime(entry.created_at)}</p>
                    </div>
                  </div>))}
            </Card>
          </section>
        </div>

        <div className="result-detail__aside">
          {canSchedule || scheduleResult ? (<Card className="result-detail__panel">
            <h2 className="result-detail__panel-title">Schedule Sitting</h2>
            <p className="result-detail__panel-description">Assign this approved item to a specific sitting date.</p>
            {canSchedule ? (<>
              <div className="result-detail__panel-field">
                <Input type="date" label="Sitting Date" value={sittingDate} onChange={(event) => setSittingDate(event.target.value)}/>
              </div>
              <div className="result-detail__panel-field">
                <Button fullWidth onClick={scheduleSubmission} disabled={isScheduling || !sittingDate}>
                  {isScheduling ? "Scheduling..." : "Schedule Item"}
                </Button>
              </div>
            </>) : null}
            {scheduleResult ? (<div className="result-detail__panel-field">
              <Toast variant="success" title="Item scheduled" description={`Scheduled for ${formatDate(scheduleResult.sitting_date)}.`}/>
            </div>) : null}
            {scheduleError ? (<div className="result-detail__panel-field">
              <Toast variant="error" title="Scheduling error" description={scheduleError}/>
            </div>) : null}
          </Card>) : null}

          {workflowActions.length > 0 ? (<Card className="result-detail__panel">
            <h2 className="result-detail__panel-title">Workflow Decision</h2>
            <p className="result-detail__panel-description">Approve, reject, or return this submission to Draft for changes.</p>

            {isWorkflowReviewable ? (<>
              <div className="result-detail__panel-field">
                <Textarea label="Workflow Notes" value={workflowNotes} onChange={(event) => setWorkflowNotes(event.target.value)} placeholder="Add guidance or reasons for this workflow decision."/>
              </div>
              <div className="result-detail__workflow-actions">
                {workflowActions.map(({ action, variant }) => (
                  <Button key={action} variant={variant} fullWidth onClick={() => recordWorkflowAction(action)} disabled={isWorkflowSaving}>
                    {isWorkflowSaving ? "Saving..." : action}
                  </Button>
                ))}
              </div>
            </>) : (<p className="result-detail__workflow-unavailable">Workflow actions are unavailable while this item is {submission.status}.</p>)}

            {workflowResult ? (<div className="result-detail__panel-field">
              <Toast variant="success" title={`${workflowResult.action} recorded`} description={`The submission is now ${workflowResult.status}.`}/>
            </div>) : null}
            {workflowError ? (<div className="result-detail__panel-field">
              <Toast variant="error" title="Workflow error" description={workflowError}/>
            </div>) : null}
          </Card>) : null}

          {hasPermission(user, "review_submission") ? (<Card className="result-detail__panel">
            <h2 className="result-detail__panel-title">Similarity Classification</h2>
            <p className="result-detail__panel-description">Classify historical similarity without changing the submission workflow status.</p>

            <fieldset className="result-detail__decisions">
              <legend className="result-detail__legend">Decision</legend>
              {["Clear (New)", "Duplicate", "Substantially Similar"].map((option) => (<label key={option} className="result-detail__decision">
                  <input type="radio" name="decision" className="result-detail__radio" checked={decision === option} onChange={() => setDecision(option)}/>
                  <span>{option}</span>
                </label>))}
            </fieldset>

            {decision !== "Clear (New)" ? (<div className="result-detail__related">
              <label className="result-detail__related-label">Related historical record</label>
              <select className="result-detail__select" value={selectedMatchId} onChange={(event) => setSelectedMatchId(event.target.value)}>
                <option value="">Select a candidate</option>
                {matches.map((result) => (<option key={result.match.id} value={result.match.id}>
                  #{result.rank} {result.match.title}
                </option>))}
              </select>
              {selectedMatch ? <p className="result-detail__selected-score">Selected similarity: {selectedMatch.match.score}%</p> : null}
            </div>) : null}

            <div className="result-detail__panel-field">
              <Textarea label="Clerk Notes" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Add reasoning, context or follow-up guidance."/>
            </div>

            {savedDecision ? (<div className="result-detail__panel-field">
                <Toast variant="success" title="Decision recorded" description="The review decision was saved to the database."/>
              </div>) : null}
            {error ? (<div className="result-detail__panel-field">
                <Toast variant="error" title="Review error" description={error}/>
              </div>) : null}

            <div className="result-detail__panel-field">
              <Button fullWidth onClick={recordDecision} disabled={isSaving || (decision !== "Clear (New)" && !selectedMatchId)}>
                {isSaving ? "Saving..." : "Record Decision"}
              </Button>
            </div>
          </Card>) : null}
        </div>
      </div>
    </div>);
}
