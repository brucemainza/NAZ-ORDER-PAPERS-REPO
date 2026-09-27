"use client";
import { useEffect, useState, useCallback } from "react";
import { SearchBar } from "@/components/search/SearchBar";
import { SubmissionCard } from "@/components/submit/SubmissionCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";

const PAGE_SIZE = 20;

export default function SearchPage() {
    const [sessions, setSessions] = useState([]);
    const [records, setRecords] = useState([]);
    const [filters, setFilters] = useState({ query: "", sessionId: "", itemType: "All", status: "All", date: "", member: "", ministry: "" });
    const [page, setPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [hasMore, setHasMore] = useState(false);
    const [responseTimeMs, setResponseTimeMs] = useState(null);

    const loadRecords = useCallback(async (applyFilters = {}, nextPage = 1) => {
        const filtersToUse = Object.keys(applyFilters).length > 0 ? applyFilters : filters;
        setFilters(filtersToUse);
        setIsLoading(true);
        setError(null);
        const startedAt = typeof performance !== "undefined" ? performance.now() : Date.now();
        try {
            const offset = (nextPage - 1) * PAGE_SIZE;
            const keywordQuery = filtersToUse.query?.trim() || "";

            if (keywordQuery.length >= 3) {
                const response = await fetch("/api/search", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        query_text: keywordQuery,
                        session_id: filtersToUse.sessionId || null,
                        item_type: filtersToUse.itemType && filtersToUse.itemType !== "All"
                            ? filtersToUse.itemType
                            : null,
                        status: filtersToUse.status && filtersToUse.status !== "All"
                            ? filtersToUse.status
                            : null,
                        date: filtersToUse.date || null,
                        member: filtersToUse.member?.trim() || null,
                        ministry: filtersToUse.ministry?.trim() || null,
                        limit: PAGE_SIZE,
                        offset,
                    }),
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) {
                    throw new Error(data.message || "Could not search submissions");
                }
                const rankedRecords = Array.isArray(data.results)
                    ? data.results.map((result) => ({
                        ...result.record,
                        search_rank: result.rank,
                        search_score: result.score,
                        matched_terms: result.matched_terms || [],
                    }))
                    : [];
                setHasMore(
                    Number(data.total_results || 0) > offset + rankedRecords.length,
                );
                setRecords(rankedRecords);
                setPage(nextPage);
                return;
            }

            const params = new URLSearchParams();
            params.append("limit", String(PAGE_SIZE + 1));
            params.append("offset", String(offset));
            if (keywordQuery) {
                params.append("query_text", keywordQuery);
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
            if (filtersToUse.date) {
                params.append("date", filtersToUse.date);
            }
            if (filtersToUse.member) {
                params.append("member", filtersToUse.member.trim());
            }
            if (filtersToUse.ministry) {
                params.append("ministry", filtersToUse.ministry.trim());
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
            const finishedAt = typeof performance !== "undefined" ? performance.now() : Date.now();
            setResponseTimeMs(Math.round(finishedAt - startedAt));
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
        const newFilters = { query: "", sessionId: "", itemType: "All", status: "All", date: "", member: "", ministry: "", ...searchFilters };
        setFilters(newFilters);
        await loadRecords(newFilters, 1);
    };

    return (<div>
      <PageHeader title="Submissions Register" showBreadcrumbs={false}/>

      <SearchBar sessions={sessions} onSearch={handleSearch} isLoading={isLoading}/>

      {responseTimeMs !== null ? (<p className="search-page__timing">
          {isLoading
            ? "Searching..."
            : `Results returned in ${responseTimeMs} ms${records.length ? ` · ${records.length} result${records.length === 1 ? "" : "s"} shown` : ""}`}
        </p>) : null}

      <section className="search-page__results">
        {isLoading ? (<div className="page-loading">
            <Spinner className="page-loading__spinner"/>
            <p className="page-loading__text">{filters.query?.trim().length >= 3 ? "Ranking matching content..." : "Loading submissions..."}</p>
          </div>) : error ? (<EmptyState title="Unable to load submissions" description={error}/>) : records.length === 0 ? (<EmptyState title="No submissions found" description="Try changing the filters or use the form above to explore current parliamentary submissions."/>) : (<div className="search-page__list">
            {records.map((record) => {
              const sessionName = sessions.find(s => s.id === record.session_id)?.name || record.session_id;
              return <SubmissionCard key={record.id} record={{...record, session_name: sessionName}} />
            })}
            <div className="search-page__pagination">
              <p className="search-page__pagination-text">Showing page {page}. {hasMore ? "More submissions are available." : "End of submissions."}</p>
              <div className="search-page__pagination-actions">
                <Button variant="secondary" size="sm" disabled={page === 1 || isLoading} onClick={() => loadRecords(filters, page - 1)}>
                  Previous
                </Button>
                <Button size="sm" disabled>{page}</Button>
                {hasMore ? <Button variant="secondary" size="sm" onClick={() => loadRecords(filters, page + 1)}>{page + 1}</Button> : null}
                <Button variant="secondary" size="sm" disabled={!hasMore || isLoading} onClick={() => loadRecords(filters, page + 1)}>
                  Next
                </Button>
              </div>
            </div>
          </div>)}
      </section>
    </div>);
}
