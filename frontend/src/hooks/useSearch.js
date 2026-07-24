"use client";
import { useState } from "react";
import { normalizeSearchResult } from "@/lib/records";

export function useSearch() {
    const [results, setResults] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);
    const [error, setError] = useState(null);
    const runSearch = async (query) => {
        setIsLoading(true);
        setError(null);
        setHasSearched(true);
        try {
            const response = await fetch("/api/search", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query_text: query.query,
                    session_id: query.sessionId || null,
                    item_type: query.itemType && query.itemType !== "All" ? query.itemType : null,
                    limit: 10,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.message || "Search failed");
            }
            setResults((data.results || []).map(normalizeSearchResult));
        } catch (err) {
            setResults([]);
            setError(err.message || "Search failed");
        } finally {
            setIsLoading(false);
        }
    };
    return {
        error,
        results,
        isLoading,
        hasSearched,
        runSearch,
    };
}
