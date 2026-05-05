import Image from "next/image";
import { LoginForm } from "@/components/auth/LoginForm";
export default function LoginPage() {
    return (<main className="min-h-screen bg-[--bg]">
      <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
        <section className="flex justify-center items-center min-h-screen bg-[--sidebar] px-8 py-12 text-[--sidebar-text]">          
          <div className="flex flex-col items-center text-center max-w-2xl">
            
            <Image
              src="/naz_logo2.jpg"
              alt="National Assembly of Zambia logo"
              width={200}
              height={200}
              className="rounded-full object-cover mb-6"
              priority
            />

            <p className="text-4xl uppercase tracking-[0.2em]">
              National Assembly of Zambia
            </p>
            <h1 className="mt-3 text-3xl font-semibold text-white">
              Order Papers System
            </h1>
          </div>
        </section>

        <section className="flex items-center justify-center px-6 py-12">
          <LoginForm />
        </section>
      </div>
    </main>);
}
