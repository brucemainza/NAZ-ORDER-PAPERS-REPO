"use client";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff } from "lucide-react";
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
    const router = useRouter();
    const { login } = useAuth();
    const [errorMessage, setErrorMessage] = useState(null);
    const [showPassword, setShowPassword] = useState(false);

    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm({
        resolver: zodResolver(loginSchema),
        defaultValues: {
            employeeId: "",
            password: "",
        },
    });

    const onSubmit = async (values) => {
        setErrorMessage(null);
        try {
            await login(values);
            router.push("/dashboard");
            router.refresh();
        } catch (error) {
            const message =
                error?.response?.data?.message ||
                "Login failed. Please confirm the employee ID is active and the password is correct.";
            setErrorMessage(message);
        }
    };

    return (
        <div className="login-form">
            <div className="login-form__header">
                <h2 className="login-form__title">Sign in</h2>
                <p className="login-form__description">
                    Authorised staff only. Use your parliamentary employee credentials.
                </p>
            </div>

            {errorMessage ? (
                <div className="login-form__error">
                    <Toast variant="error" title="Authentication error" description={errorMessage} />
                </div>
            ) : null}

            <form className="login-form__fields" onSubmit={handleSubmit(onSubmit)}>
                <Input
                    id="employeeId"
                    label="Employee ID"
                    placeholder="EMP-001"
                    error={errors.employeeId?.message}
                    {...register("employeeId")}
                />

                <div className="login-form__password">
                    <Input
                        id="password"
                        label="Password"
                        type={showPassword ? "text" : "password"}
                        placeholder="Enter your password"
                        error={errors.password?.message}
                        {...register("password")}
                    />
                    <button
                        type="button"
                        onClick={() => setShowPassword((prev) => !prev)}
                        className="login-form__password-toggle"
                        tabIndex={-1}
                        aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                </div>

                <Button type="submit" fullWidth disabled={isSubmitting}>
                    {isSubmitting ? (
                        <>
                            <Spinner />
                            Signing in...
                        </>
                    ) : (
                        "Access portal"
                    )}
                </Button>
            </form>
        </div>
    );
}
