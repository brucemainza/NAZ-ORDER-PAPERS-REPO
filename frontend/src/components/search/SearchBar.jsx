"use client";

import { ChevronDown, ChevronUp, Filter, RotateCcw, Search as SearchIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";

const EMPTY_FILTERS = {
    sessionId: "",
    itemType: "All",
    status: "All",
    date: "",
    member: "",
    ministry: "",
};

function countFilters(filters) {
    return [
        filters.sessionId,
        filters.itemType !== "All" ? filters.itemType : "",
        filters.status !== "All" ? filters.status : "",
        filters.date,
        filters.member.trim(),
        filters.ministry.trim(),
    ].filter(Boolean).length;
}

export function SearchBar({ sessions, onSearch, isLoading }) {
    const [query, setQuery] = useState("");
    const [isFilterPanelOpen, setIsFilterPanelOpen] = useState(false);
    const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS);
    const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);
    const appliedFilterCount = useMemo(() => countFilters(appliedFilters), [appliedFilters]);

    const updateDraftFilter = (name, value) => {
        setDraftFilters((current) => ({ ...current, [name]: value }));
    };

    const runSearch = (filters = appliedFilters) => {
        onSearch({ query, ...filters });
    };

    const applyFilters = () => {
        const nextFilters = { ...draftFilters };
        setAppliedFilters(nextFilters);
        runSearch(nextFilters);
        setIsFilterPanelOpen(false);
    };

    const resetFilters = () => {
        const nextFilters = { ...EMPTY_FILTERS };
        setDraftFilters(nextFilters);
        setAppliedFilters(nextFilters);
        runSearch(nextFilters);
    };

    return (
        <form
            className="search-bar"
            onSubmit={(event) => {
                event.preventDefault();
                runSearch();
            }}
        >
            <div className="search-bar__primary-row">
                <div className="search-bar__query">
                    <Input
                        id="searchQuery"
                        label="Search submissions"
                        placeholder="Search by keyword, subject or member name..."
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                    />
                </div>
                <Button type="submit" className="search-bar__button" disabled={isLoading}>
                    <SearchIcon className="search-bar__icon" />
                    {isLoading ? "Searching..." : "Search"}
                </Button>
            </div>

            <div className="search-bar__filter-toggle-row">
                <Button
                    type="button"
                    variant="secondary"
                    className="search-bar__filter-toggle"
                    aria-expanded={isFilterPanelOpen}
                    aria-controls="submission-filters"
                    onClick={() => setIsFilterPanelOpen((current) => !current)}
                >
                    <Filter className="search-bar__filter-icon" />
                    Filters
                    {appliedFilterCount > 0 ? (
                        <span className="search-bar__filter-count">{appliedFilterCount}</span>
                    ) : null}
                    {isFilterPanelOpen ? (
                        <ChevronUp className="search-bar__chevron" />
                    ) : (
                        <ChevronDown className="search-bar__chevron" />
                    )}
                </Button>
            </div>

            {isFilterPanelOpen ? (
                <div id="submission-filters" className="search-bar__filter-panel">
                    <div className="search-bar__filter-grid">
                        <Select
                            id="searchSession"
                            label="Session"
                            value={draftFilters.sessionId}
                            onChange={(event) => updateDraftFilter("sessionId", event.target.value)}
                        >
                            <option value="">All sessions</option>
                            {sessions.map((session) => (
                                <option key={session.id} value={session.id}>{session.name}</option>
                            ))}
                        </Select>
                        <Select
                            id="searchType"
                            label="Item Type"
                            value={draftFilters.itemType}
                            onChange={(event) => updateDraftFilter("itemType", event.target.value)}
                        >
                            <option value="All">All items</option>
                            <option value="Question">Question</option>
                            <option value="Motion">Motion</option>
                        </Select>
                        <Select
                            id="searchStatus"
                            label="Status"
                            value={draftFilters.status}
                            onChange={(event) => updateDraftFilter("status", event.target.value)}
                        >
                            <option value="All">All statuses</option>
                            <option value="Draft">Draft</option>
                            <option value="Submitted">Submitted</option>
                            <option value="Under Review">Under Review</option>
                            <option value="Approved">Approved</option>
                            <option value="Rejected">Rejected</option>
                            <option value="Scheduled">Scheduled</option>
                            <option value="Archived">Archived</option>
                        </Select>
                        <Input
                            id="searchDate"
                            type="date"
                            label="Submission date"
                            value={draftFilters.date}
                            onChange={(event) => updateDraftFilter("date", event.target.value)}
                        />
                        <Input
                            id="searchMember"
                            label="Member"
                            placeholder="Filter by member"
                            value={draftFilters.member}
                            onChange={(event) => updateDraftFilter("member", event.target.value)}
                        />
                        <Input
                            id="searchMinistry"
                            label="Ministry"
                            placeholder="Filter by ministry"
                            value={draftFilters.ministry}
                            onChange={(event) => updateDraftFilter("ministry", event.target.value)}
                        />
                    </div>
                    <div className="search-bar__filter-actions">
                        <Button type="button" onClick={applyFilters} disabled={isLoading}>
                            Apply filters
                        </Button>
                        {appliedFilterCount > 0 || countFilters(draftFilters) > 0 ? (
                            <Button type="button" variant="secondary" onClick={resetFilters} disabled={isLoading}>
                                <RotateCcw className="search-bar__reset-icon" />
                                Reset filters
                            </Button>
                        ) : null}
                    </div>
                </div>
            ) : null}
        </form>
    );
}
