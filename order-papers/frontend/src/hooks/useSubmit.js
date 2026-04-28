"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { buildSimilarityResultsForSubmission } from "@/lib/mockData";
const LOCAL_SUBMISSIONS_KEY = "naz-local-submissions";
const LOCAL_MATCHES_KEY = "naz-local-matches";
export function useSubmit() {
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const submitSubmission = async (values, submittedBy) => {
        var _a, _b;
        setIsSubmitting(true);
        const id = `sub-local-${Date.now()}`;
        const createdSubmission = {
            ...values,
            id,
            submittedAt: new Date().toISOString(),
            submittedBy,
            status: "Pending",
        };
        const matches = buildSimilarityResultsForSubmission(createdSubmission);
        if (typeof window !== "undefined") {
            const storedSubmissions = JSON.parse((_a = window.localStorage.getItem(LOCAL_SUBMISSIONS_KEY)) !== null && _a !== void 0 ? _a : "[]");
            const storedMatches = JSON.parse((_b = window.localStorage.getItem(LOCAL_MATCHES_KEY)) !== null && _b !== void 0 ? _b : "{}");
            window.localStorage.setItem(LOCAL_SUBMISSIONS_KEY, JSON.stringify([createdSubmission, ...storedSubmissions]));
            window.localStorage.setItem(LOCAL_MATCHES_KEY, JSON.stringify({
                ...storedMatches,
                [id]: matches,
            }));
        }
        await new Promise((resolve) => setTimeout(resolve, 900));
        setIsSubmitting(false);
        router.push(`/results/${id}`);
    };
    return {
        isSubmitting,
        submitSubmission,
    };
}
