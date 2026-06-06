import { PageHeader } from "@/components/layout/PageHeader";
import { SubmitForm } from "@/components/submit/SubmitForm";
import { mockSessions } from "@/lib/mockData";
export default function SubmitPage() {
    return (<div>
      <PageHeader title="New Submission" description="Capture a draft parliamentary question or motion, then run a similarity review before it proceeds."/>
      <SubmitForm sessions={mockSessions}/>
    </div>);
}
