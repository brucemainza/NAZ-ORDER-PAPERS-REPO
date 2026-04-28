"use client";
import { SearchBar } from "@/components/search/SearchBar";
import { ResultCard } from "@/components/search/ResultCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { useSearch } from "@/hooks/useSearch";
import { mockSessions } from "@/lib/mockData";
export default function SearchPage() {
    const { results, isLoading, hasSearched, runSearch } = useSearch();
    return (<div>
      <PageHeader title="Search Historical Records" description="Search indexed parliamentary records to detect exact or semantically similar historical items."/>

      <SearchBar sessions={mockSessions} onSearch={runSearch} isLoading={isLoading}/>

      <section className="mt-6 space-y-4">
        {isLoading ? (<div className="rounded-md border border-[--border] bg-white px-6 py-10 text-center shadow-sm">
            <Spinner className="mx-auto h-6 w-6"/>
            <p className="mt-3 text-sm text-[--muted]">Searching the parliamentary archive...</p>
          </div>) : !hasSearched ? (<EmptyState title="No search has been run" description="Enter keywords, select an optional session filter, and review ranked similarity matches drawn from the mock archive."/>) : results.length === 0 ? (<EmptyState title="No matching records found" description="Try broadening the search terms or removing filters to explore more of the historical archive."/>) : (results.map((result) => <ResultCard key={result.match.id} result={result}/>))}
      </section>
    </div>);
}
