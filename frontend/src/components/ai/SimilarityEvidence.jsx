"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { createExplanationAI, getExplanationAI } from "@/lib/api";

export default function SimilarityEvidence({ queryText, matches }) {
    const [explanation, setExplanation] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!queryText || !matches || matches.length === 0) return;

        const recordIds = matches.slice(0, 3).map((m) => m.match.id);
        setLoading(true);
        setError(null);

        let cancelled = false;
        let timer;
        const poll = async (runId) => {
            const response = await getExplanationAI(runId);
            if (cancelled) return;
            if (response.data.status === "completed" || response.data.status === "failed") {
                setExplanation(response.data.result);
                setError(response.data.error || null);
                setLoading(false);
                return;
            }
            timer = window.setTimeout(() => poll(runId), 1000);
        };
        createExplanationAI(queryText, recordIds)
            .then((response) => {
                if (response.data.result) {
                    setExplanation(response.data.result);
                    setLoading(false);
                    return;
                }
                return poll(response.data.run_id);
            })
            .catch((err) => {
                if (!cancelled) {
                    setError(err?.response?.data?.message || "Could not load AI explanation");
                    setLoading(false);
                }
            });
        return () => {
            cancelled = true;
            if (timer) window.clearTimeout(timer);
        };
    }, [queryText, matches]);

    if (!matches || matches.length === 0) return null;

    return (
        <Card className="ai-evidence">
            <h3 className="ai-evidence__title">AI Similarity Evidence</h3>
            <p className="ai-evidence__description">
                Hybrid lexical + semantic retrieval ranked the following historical records.
            </p>

            <ul className="ai-evidence__matches">
                {matches.map((result) => (
                    <li key={result.match.id} className="ai-evidence__match">
                        <span className="ai-evidence__rank">#{result.rank}</span>
                        <span className="ai-evidence__subject">{result.match.title}</span>
                        <span className="ai-evidence__score">
                            {result.match.score}% ranking score
                        </span>
                    </li>
                ))}
            </ul>

            {loading && (
                <div className="ai-evidence__loading">
                    <Spinner size="sm" />
                    <span>Generating grounded explanation...</span>
                </div>
            )}

            {error && <p className="ai-evidence__error">{error}</p>}

            {explanation && !loading && (
                <div className="ai-evidence__explanation">
                    <p className="ai-evidence__classification">
                        Classification: <strong>{explanation.classification}</strong>
                        {" "}(confidence: {explanation.confidence})
                    </p>
                    <p className="ai-evidence__summary">{explanation.summary}</p>
                    {explanation.human_review_required && (
                        <p className="ai-evidence__review">
                            Human review is required before a final procedural decision.
                        </p>
                    )}
                </div>
            )}
        </Card>
    );
}
