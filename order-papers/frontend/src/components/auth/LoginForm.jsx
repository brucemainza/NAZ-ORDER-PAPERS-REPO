"use client";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { Toast } from "@/components/ui/Toast";
import { useAuth } from "@/hooks/useAuth";
const loginSchema = z.object({
    employeeId: z.string().min(1, "Employee ID is required"),
    password: z.string().min(1, "Password is required"),
});
export function LoginForm() {
    var _a, _b;
    const router = useRouter();
    const { login } = useAuth();
    const [errorMessage, setErrorMessage] = useState(null);
    const { register, handleSubmit, formState: { errors, isSubmitting }, } = useForm({
        resolver: zodResolver(loginSchema),
        defaultValues: {
            employeeId: "EMP-001",
            password: "Password123!",
        },
    });
    const onSubmit = async (values) => {
        setErrorMessage(null);
        try {
            await login(values);
            router.push("/dashboard");
            router.refresh();
        }
        catch (error) {
            setErrorMessage("Login failed. Please confirm the employee ID is active and the password is correct.");
        }
    };
    return (<div className="w-full max-w-md rounded-md border border-[--border] bg-white p-8 shadow-sm">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-[--black]">Sign in</h2>
        <p className="mt-2 text-sm text-[--muted]">Authorised staff only. Use your parliamentary employee credentials.</p>
      </div>

      {errorMessage ? (<div className="mb-4">
          <Toast variant="error" title="Authentication error" description={errorMessage}/>
        </div>) : null}

      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
        <Input id="employeeId" label="Employee ID" placeholder="EMP-001" error={(_a = errors.employeeId) === null || _a === void 0 ? void 0 : _a.message} {...register("employeeId")}/>
        <Input id="password" label="Password" type="password" placeholder="Enter your password" error={(_b = errors.password) === null || _b === void 0 ? void 0 : _b.message} {...register("password")}/>
        <div className="rounded-md border border-[--border] bg-[--bg] px-3 py-3 text-xs text-[--muted]">
          Demo access: use `EMP-001` to `EMP-005` with the shared password `Password123!`.
        </div>
        <Button type="submit" fullWidth disabled={isSubmitting}>
          {isSubmitting ? (<>
              <Spinner />
              Signing in...
            </>) : ("Access portal")}
        </Button>
      </form>
    </div>);
}
