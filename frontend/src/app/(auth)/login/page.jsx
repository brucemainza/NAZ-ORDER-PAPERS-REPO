import Image from "next/image";
import { LoginForm } from "@/components/auth/LoginForm";
export default function LoginPage() {
    return (<main className="login-page">
      <div className="login-page__grid">
        <section className="login-page__identity">
          <div className="login-page__brand">
            
            <Image
              src="/naz_logo2.jpg"
              alt="National Assembly of Zambia logo"
              width={200}
              height={200}
              className="login-page__logo"
              priority
            />

            <p className="login-page__eyebrow">
              National Assembly of Zambia
            </p>
            <h1 className="login-page__title">
              Order Papers System
            </h1>
          </div>
        </section>

        <section className="login-page__form">
          <LoginForm />
        </section>
      </div>
    </main>);
}
