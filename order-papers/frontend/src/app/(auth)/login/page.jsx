import { LoginForm } from "@/components/auth/LoginForm";
export default function LoginPage() {
    return (<main className="min-h-screen bg-[--bg]">
      <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
        <section className="flex items-center bg-[--sidebar] px-8 py-12 text-[--sidebar-text]">
          <div className="mx-auto max-w-xl">
            <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-md border border-white/15 bg-[--primary] text-lg font-semibold text-white">
              NAZ
            </div>
            <p className="text-xs uppercase tracking-[0.2em] text-[--sidebar-text]">National Assembly of Zambia</p>
            <h1 className="mt-3 text-3xl font-semibold text-white">Order Papers System</h1>
            <p className="mt-4 max-w-lg text-sm leading-6 text-[--sidebar-text]">
              National Assembly of Zambia — Internal Portal for managing parliamentary questions, motions and historical similarity review.
            </p>
            <div className="mt-8 grid gap-3 text-sm">
            </div>
          </div>
        </section>

        <section className="flex items-center justify-center px-6 py-12">
          <LoginForm />
        </section>
      </div>
    </main>);
}
