import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
export default function DashboardLayout({ children }) {
    return (<div className="min-h-screen bg-[--bg] md:grid md:grid-cols-[272px_1fr]">
      <Sidebar />
      <div className="min-w-0">
        <Topbar />
        <main className="px-4 py-6 md:px-6">{children}</main>
      </div>
    </div>);
}
