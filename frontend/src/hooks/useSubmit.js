"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";

export function useSubmit() {
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const submitSubmission = async (values, { confirmDuplicate = false } = {}) => {
        setIsSubmitting(true);
        setError(null);
        try {
            const response = await fetch("/api/submissions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    item_type: values.type,
                    session_id: values.sessionId,
                    member: values.member,
                    ministry: values.ministry || null,
                    answer_type: values.answerType,
                    subject: values.subject,
                    full_text: values.fullText,
                    confirm_duplicate: confirmDuplicate,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (response.status === 409 && data.duplicate) {
                return { duplicate: data.duplicate };
            }
            if (!response.ok) {
                throw new Error(data.message || "Submission failed");
            }
            router.push(`/results/${data.record.id}`);
            return { success: true };
        } catch (err) {
            setError(err.message || "Submission failed");
            return { success: false };
        } finally {
            setIsSubmitting(false);
        }
    };
    return {
        error,
        isSubmitting,
        submitSubmission,
    };
}
