"use client";
import { Search as SearchIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
export function SearchBar({ sessions, onSearch, isLoading, }) {
    const [query, setQuery] = useState("");
    const [sessionId, setSessionId] = useState("");
    const [itemType, setItemType] = useState("All");
    const [status, setStatus] = useState("All");
    const debounceTimerRef = useRef(null);

    const applyFilters = () => {
        onSearch({ query, sessionId: sessionId || undefined, itemType, status });
    };

    useEffect(() => {
        // Debounce filter changes - apply filters 500ms after user stops changing them
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }
        debounceTimerRef.current = setTimeout(() => {
            applyFilters();
        }, 500);

        return () => {
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
        };
    }, [query, sessionId, itemType, status]);

    return (<form className="search-bar" onSubmit={async (event) => {
            event.preventDefault();
            applyFilters();
        }}>
      <div className="search-bar__grid">
        <Input id="searchQuery" label="Search text" placeholder="Enter keywords, member name, subject or ministry" value={query} onChange={(event) => setQuery(event.target.value)}/>
        <Select id="searchSession" label="Session" value={sessionId} onChange={(event) => setSessionId(event.target.value)}>
          <option value="">All sessions</option>
          {sessions.map((session) => (<option key={session.id} value={session.id}>
              {session.name}
            </option>))}
        </Select>
        <Select id="searchType" label="Item Type" value={itemType} onChange={(event) => setItemType(event.target.value)}>
          <option value="All">All items</option>
          <option value="Question">Question</option>
          <option value="Motion">Motion</option>
        </Select>
        <Select id="searchStatus" label="Status" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="All">All statuses</option>
          <option value="Draft">Draft</option>
          <option value="Submitted">Submitted</option>
          <option value="Under Review">Under Review</option>
          <option value="Approved">Approved</option>
          <option value="Rejected">Rejected</option>
          <option value="Scheduled">Scheduled</option>
          <option value="Archived">Archived</option>
        </Select>
        <div className="search-bar__action">
          <Button type="submit" className="search-bar__button" disabled={isLoading}>
            <SearchIcon className="search-bar__icon"/>
            {isLoading ? "Searching..." : "Search"}
          </Button>
        </div>
      </div>
    </form>);
}
