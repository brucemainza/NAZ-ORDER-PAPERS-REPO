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

    return (<form className="rounded-md border border-[--border] bg-white p-5 shadow-sm" onSubmit={async (event) => {
            event.preventDefault();
            applyFilters();
        }}>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
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
          <option value="Pending Review">Pending Review</option>
          <option value="Duplicate">Duplicate</option>
          <option value="Historical">Historical</option>
          <option value="Clear">Clear</option>
        </Select>
        <div className="flex items-end">
          <Button type="submit" className="w-full lg:w-auto" disabled={isLoading}>
            <SearchIcon className="h-4 w-4"/>
            {isLoading ? "Searching..." : "Search"}
          </Button>
        </div>
      </div>
    </form>);
}
