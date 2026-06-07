"use client";
import Link from "next/link";
import { useEffect, useState, useCallback } from "react";
import { SearchBar } from "@/components/search/SearchBar";
import { SubmissionCard } from "@/components/submit/SubmissionCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";

const PAGE_SIZE = 15;

export default function SearchPage() {
    const [sessions, setSessions] = useState([]);
    const [records, setRecords] = useState([]);
    const [filters, setFilters] = useState({ query: "", sessionId: "", itemType: "All", status: "All" });
    const [page, setPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [hasMore, setHasMore] = useState(false);

    const loadRecords = useCallback(async (applyFilters = {}, nextPage = 1) => {
        const filtersToUse = Object.keys(applyFilters).length > 0 ? applyFilters : filters;
        setFilters(filtersToUse);
        setIsLoading(true);
        setError(null);
        try {
            const params = new URLSearchParams();
            const offset = (nextPage - 1) * PAGE_SIZE;
            params.append("limit", String(PAGE_SIZE + 1));
            params.append("offset", String(offset));
            if (filtersToUse.query) {
                params.append("query_text", filtersToUse.query.trim());
            }
            if (filtersToUse.sessionId) {
                params.append("session_id", filtersToUse.sessionId);
            }
            if (filtersToUse.itemType && filtersToUse.itemType !== "All") {
                params.append("item_type", filtersToUse.itemType);
            }
            if (filtersToUse.status && filtersToUse.status !== "All") {
                params.append("status", filtersToUse.status);
            }
            const response = await fetch(`/api/records?${params.toString()}`);
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.message || "Could not load submissions");
            }
            setHasMore(Array.isArray(data) && data.length > PAGE_SIZE);
            setRecords(Array.isArray(data) ? data.slice(0, PAGE_SIZE) : []);
            setPage(nextPage);
        } catch (err) {
            setError(err.message || "Could not load submissions");
            setRecords([]);
            setHasMore(false);
        } finally {
            setIsLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        fetch("/api/sessions")
            .then((response) => response.json())
            .then((data) => setSessions(Array.isArray(data) ? data : []))
            .catch(() => setSessions([]));
        loadRecords({}, 1);
    }, []);

    const handleSearch = async (searchFilters) => {
        const newFilters = { query: "", sessionId: "", itemType: "All", status: "All", ...searchFilters };
        setFilters(newFilters);
        await loadRecords(newFilters, 1);
    };

    return (<div>
      <PageHeader title="Submissions" description="Browse all parliamentary submissions and filter by session, item type, status, or text." actions={<Link href="/submit"><Button variant="primary">New Submission</Button></Link>}/>

      <SearchBar sessions={sessions} onSearch={handleSearch} isLoading={isLoading}/>

      <section className="mt-6 space-y-4">
        {isLoading ? (<div className="rounded-md border border-[--border] bg-white px-6 py-10 text-center shadow-sm">
            <Spinner className="mx-auto h-6 w-6"/>
            <p className="mt-3 text-sm text-[--muted]">Loading submissions...</p>
          </div>) : error ? (<EmptyState title="Unable to load submissions" description={error}/>) : records.length === 0 ? (<EmptyState title="No submissions found" description="Try changing the filters or use the form above to explore current parliamentary submissions."/>) : (<div className="space-y-4">
            {records.map((record) => {
              const sessionName = sessions.find(s => s.id === record.session_id)?.name || record.session_id;
              return <SubmissionCard key={record.id} record={{...record, sessionName}} />
            })}
            <div className="flex flex-col gap-3 rounded-md border border-[--border] bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-[--muted]">Showing page {page}. {hasMore ? "More submissions are available." : "End of submissions."}</p>
              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" disabled={page === 1 || isLoading} onClick={() => loadRecords(filters, page - 1)}>
                  Previous
                </Button>
                <Button variant="secondary" size="sm" disabled={!hasMore || isLoading} onClick={() => loadRecords(filters, page + 1)}>
                  Next
                </Button>
              </div>
            </div>
          </div>)}
      </section>
    </div>);
}
