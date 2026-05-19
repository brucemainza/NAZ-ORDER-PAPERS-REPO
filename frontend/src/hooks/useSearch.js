"use client";
import { useState } from "react";
import { searchHistoricalRecords } from "@/lib/mockData";
export function useSearch() {
    const [results, setResults] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);
    const runSearch = async (query) => {
        setIsLoading(true);
        setHasSearched(true);
        await new Promise((resolve) => setTimeout(resolve, 650));
        setResults(searchHistoricalRecords(query));
        setIsLoading(false);
    };
    return {
        results,
        isLoading,
        hasSearched,
        runSearch,
    };
}
