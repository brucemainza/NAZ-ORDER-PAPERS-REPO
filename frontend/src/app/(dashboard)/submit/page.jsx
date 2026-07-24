"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/layout/PageHeader";
import { SubmitForm } from "@/components/submit/SubmitForm";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { useAuthContext } from "@/context/AuthContext";
import { hasPermission } from "@/lib/auth";

export default function SubmitPage() {
    const { user, isLoading: isAuthLoading } = useAuthContext();
    const [sessions, setSessions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const itemTypes = [];
    if (hasPermission(user, "submit_question")) {
        itemTypes.push("Question");
    }
    if (hasPermission(user, "submit_motion")) {
        itemTypes.push("Motion");
    }
    useEffect(() => {
        fetch("/api/sessions")
            .then((response) => response.json())
            .then((data) => setSessions(Array.isArray(data) ? data : []))
            .finally(() => setIsLoading(false));
    }, []);
    return (<div>
      <PageHeader title="New Submission" description="Capture a draft parliamentary question or motion, then run a similarity review before it proceeds." actions={<Link href="/search"><Button variant="primary">View All Submissions</Button></Link>}/>
      {isLoading || isAuthLoading ? (<div className="page-loading">
          <Spinner className="page-loading__spinner"/>
          <p className="page-loading__text">Loading parliamentary sessions...</p>
        </div>) : itemTypes.length === 0 ? (<EmptyState title="Submission access required" description="Your account does not have permission to submit questions or motions."/>) : sessions.length === 0 ? (<EmptyState title="No sessions available" description="Add or activate a parliamentary session before creating submissions."/>) : (<SubmitForm sessions={sessions} itemTypes={itemTypes}/>)}
    </div>);
}
