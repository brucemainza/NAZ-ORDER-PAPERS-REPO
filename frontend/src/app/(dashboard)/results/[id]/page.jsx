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
import { Textarea } from "@/components/ui/Textarea";
import { Toast } from "@/components/ui/Toast";
import { useAuth } from "@/hooks/useAuth";
import { buildSimilarityResultsForSubmission, getAuditTrailForItem, getDecisionHistory, getSessionById, getSubmissionById, mockSimilarityResults, } from "@/lib/mockData";
import { formatDate, formatDateTime } from "@/lib/utils";
const LOCAL_SUBMISSIONS_KEY = "naz-local-submissions";
const LOCAL_MATCHES_KEY = "naz-local-matches";
const LOCAL_DECISIONS_KEY = "naz-local-decisions";
export default function ResultDetailPage() {
    const params = useParams();
    const { user } = useAuth();
    const [submission, setSubmission] = useState(null);
    const [matches, setMatches] = useState([]);
    const [decision, setDecision] = useState("Clear (New)");
    const [notes, setNotes] = useState("");
    const [savedDecision, setSavedDecision] = useState(false);
    const [history, setHistory] = useState([]);
    const [isHistoricalRecord, setIsHistoricalRecord] = useState(false);
    useEffect(() => {
        var _a, _b, _c, _d, _e;
        const id = params.id;
        const localSubmissions = JSON.parse((_a = window.localStorage.getItem(LOCAL_SUBMISSIONS_KEY)) !== null && _a !== void 0 ? _a : "[]");
        const localMatches = JSON.parse((_b = window.localStorage.getItem(LOCAL_MATCHES_KEY)) !== null && _b !== void 0 ? _b : "{}");
        const localDecisions = JSON.parse((_c = window.localStorage.getItem(LOCAL_DECISIONS_KEY)) !== null && _c !== void 0 ? _c : "[]");
        const knownSubmission = (_d = localSubmissions.find((item) => item.id === id)) !== null && _d !== void 0 ? _d : getSubmissionById(id);
        const historicalMatch = mockSimilarityResults.find((item) => item.id === id || item.sourceSubmissionId === id);
        if (knownSubmission) {
            setSubmission(knownSubmission);
            setMatches((_e = localMatches[id]) !== null && _e !== void 0 ? _e : buildSimilarityResultsForSubmission(knownSubmission));
            setHistory([...getDecisionHistory(knownSubmission.id), ...localDecisions.filter((entry) => entry.submissionId === knownSubmission.id)]);
            setIsHistoricalRecord(false);
            return;
        }
        if (historicalMatch) {
            setSubmission({
                id: historicalMatch.id,
                type: historicalMatch.itemType,
                sessionId: historicalMatch.sessionId,
                member: historicalMatch.member,
                ministry: historicalMatch.ministry,
                subject: historicalMatch.title,
                fullText: historicalMatch.fullText,
                submittedBy: historicalMatch.member,
                submittedAt: historicalMatch.date,
                status: "Reviewed",
            });
            setMatches(mockSimilarityResults
                .filter((item) => item.id !== historicalMatch.id)
                .sort((left, right) => right.score - left.score)
                .slice(0, 4)
                .map((match, index) => ({ rank: index + 1, match })));
            setHistory(localDecisions.filter((entry) => entry.submissionId === historicalMatch.id));
            setIsHistoricalRecord(true);
            return;
        }
        setSubmission(null);
    }, [params.id]);
    const session = useMemo(() => (submission ? getSessionById(submission.sessionId) : null), [submission]);
    const auditTrail = useMemo(() => {
        if (!submission) {
            return [];
        }
        return getAuditTrailForItem(submission.id);
    }, [submission]);
    if (!submission) {
        return (<div>
        <PageHeader title="Result Record" description="Detailed submission review and historical similarity context."/>
        <EmptyState title="Record not found" description="The requested submission or historical match could not be located in the demo dataset."/>
      </div>);
    }
    const recordDecision = () => {
        var _a, _b;
        const newEntry = {
            id: `decision-local-${Date.now()}`,
            submissionId: submission.id,
            decision,
            notes,
            decidedBy: (_a = user === null || user === void 0 ? void 0 : user.name) !== null && _a !== void 0 ? _a : "Authenticated Clerk",
            decidedAt: new Date().toISOString(),
        };
        const existing = JSON.parse((_b = window.localStorage.getItem(LOCAL_DECISIONS_KEY)) !== null && _b !== void 0 ? _b : "[]");
        window.localStorage.setItem(LOCAL_DECISIONS_KEY, JSON.stringify([newEntry, ...existing]));
        setHistory((current) => [newEntry, ...current]);
        setSavedDecision(true);
        setNotes("");
    };
    return (<div>
      <PageHeader title="Result Record" description="Review the submitted item, inspect ranked similarity matches and capture the clerk's decision." actions={<Link href="/search" className={buttonStyles({ variant: "secondary" })}>
            Back to Search
          </Link>}/>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_360px]">
        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={submission.type === "Question" ? "question" : "motion"}>{submission.type}</Badge>
              <Badge variant="reviewed">{submission.status}</Badge>
              {session ? <Badge variant="info">{session.name}</Badge> : null}
            </div>
            <h2 className="mt-4 text-xl font-semibold text-[--black]">{submission.subject}</h2>
            <div className="mt-3 flex flex-wrap gap-4 text-sm text-[--muted]">
              <span>Member: {submission.member}</span>
              <span>Submitted by: {submission.submittedBy}</span>
              <span>Date: {formatDate(submission.submittedAt)}</span>
              {submission.ministry ? <span>Ministry: {submission.ministry}</span> : null}
            </div>
            <div className="mt-5 rounded-md border border-[--border] bg-[--bg] p-4 text-sm leading-6 text-[--black]">
              {submission.fullText}
            </div>
          </Card>

          <section className="space-y-4">
            <div>
              <h2 className="text-base font-medium text-[--black]">Similarity Matches</h2>
              <p className="text-sm text-[--muted]">Ranked historical records related to this submission.</p>
            </div>
            {matches.length === 0 ? (<EmptyState title="No similarity matches available" description="No mock similarity results were generated for this record."/>) : (matches.map((result) => <ResultCard key={result.match.id} result={result} expandable initiallyExpanded={result.rank === 1}/>))}
          </section>

          <section className="space-y-4">
            <div>
              <h2 className="text-base font-medium text-[--black]">Audit Trail</h2>
              <p className="text-sm text-[--muted]">Related activity and recorded decisions for this record.</p>
            </div>

            <Card className="divide-y divide-[--border]">
              {[...history.map((entry) => ({
                id: entry.id,
                title: entry.decision,
                detail: entry.notes || "No decision notes captured.",
                meta: `${entry.decidedBy} • ${formatDateTime(entry.decidedAt)}`,
            })),
            ...auditTrail.map((entry) => ({
                id: entry.id,
                title: entry.action,
                detail: `${entry.user} from ${entry.ipAddress}`,
                meta: formatDateTime(entry.date),
            }))].length === 0 ? (<div className="px-5 py-6 text-sm text-[--muted]">No audit entries are available for this record yet.</div>) : ([...history.map((entry) => ({
                id: entry.id,
                title: entry.decision,
                detail: entry.notes || "No decision notes captured.",
                meta: `${entry.decidedBy} • ${formatDateTime(entry.decidedAt)}`,
            })),
            ...auditTrail.map((entry) => ({
                id: entry.id,
                title: entry.action,
                detail: `${entry.user} from ${entry.ipAddress}`,
                meta: formatDateTime(entry.date),
            }))].map((entry) => (<div key={entry.id} className="px-5 py-4">
                    <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                      <div>
                        <p className="font-medium text-[--black]">{entry.title}</p>
                        <p className="mt-1 text-sm text-[--muted]">{entry.detail}</p>
                      </div>
                      <p className="text-xs text-[--muted]">{entry.meta}</p>
                    </div>
                  </div>)))}
            </Card>
          </section>
        </div>

        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="text-base font-medium text-[--black]">{isHistoricalRecord ? "Historical Record View" : "Clerk Decision Panel"}</h2>
            <p className="mt-1 text-sm text-[--muted]">
              {isHistoricalRecord
            ? "This record was opened from historical search results. Similarity decisions are only recorded on submitted items."
            : "Record the review outcome for the submitted item and keep a note for future audit reference."}
            </p>

            {isHistoricalRecord ? (<div className="mt-4 rounded-md border border-[--border] bg-[--bg] px-4 py-4 text-sm text-[--muted]">
                Historical records remain read-only in this scaffold. Submit a new item to test the decision workflow end-to-end.
              </div>) : (<>
                <fieldset className="mt-5 space-y-3">
                  <legend className="text-sm font-medium text-[--black]">Decision</legend>
                  {["Clear (New)", "Duplicate", "Substantially Similar"].map((option) => (<label key={option} className="flex items-center gap-2 rounded-md border border-[--border] bg-[--bg] px-3 py-2 text-sm">
                      <input type="radio" name="decision" className="h-4 w-4 accent-[--primary]" checked={decision === option} onChange={() => setDecision(option)}/>
                      <span>{option}</span>
                    </label>))}
                </fieldset>

                <div className="mt-4">
                  <Textarea label="Clerk Notes" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Add reasoning, context or follow-up guidance."/>
                </div>

                {savedDecision ? (<div className="mt-4">
                    <Toast variant="success" title="Decision recorded" description="The review decision was saved to local demo storage."/>
                  </div>) : null}

                <div className="mt-4">
                  <Button fullWidth onClick={recordDecision}>
                    Record Decision
                  </Button>
                </div>
              </>)}
          </Card>
        </div>
      </div>
    </div>);
}
