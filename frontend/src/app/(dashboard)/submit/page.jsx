"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/layout/PageHeader";
import { SubmitForm } from "@/components/submit/SubmitForm";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";

export default function SubmitPage() {
    const [sessions, setSessions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    useEffect(() => {
        fetch("/api/sessions")
            .then((response) => response.json())
            .then((data) => setSessions(Array.isArray(data) ? data : []))
            .finally(() => setIsLoading(false));
    }, []);
    return (<div>
      <PageHeader title="New Submission" description="Capture a draft parliamentary question or motion, then run a similarity review before it proceeds." actions={<Link href="/search"><Button variant="primary">View All Submissions</Button></Link>}/>
      {isLoading ? (<div className="page-loading">
          <Spinner className="page-loading__spinner"/>
          <p className="page-loading__text">Loading parliamentary sessions...</p>
        </div>) : sessions.length === 0 ? (<EmptyState title="No sessions available" description="Add or activate a parliamentary session before creating submissions."/>) : (<SubmitForm sessions={sessions}/>)}
    </div>);
}
