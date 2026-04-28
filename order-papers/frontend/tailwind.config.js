export default {
    content: ["./src/app/**/*.{js,jsx}", "./src/components/**/*.{js,jsx}", "./src/context/**/*.{js,jsx}", "./src/hooks/**/*.{js,jsx}"],
    theme: {
        extend: {
            colors: {
                primary: "var(--primary)",
                "primary-dark": "var(--primary-dark)",
                "primary-light": "var(--primary-light)",
                accent: "var(--accent)",
                "accent-light": "var(--accent-light)",
                ink: "var(--black)",
                surface: "var(--surface)",
                bg: "var(--bg)",
                border: "var(--border)",
                muted: "var(--muted)",
                sidebar: "var(--sidebar)",
                "sidebar-text": "var(--sidebar-text)",
                danger: "var(--danger)",
                success: "var(--success)"
            },
            boxShadow: {
                sm: "0 1px 2px 0 rgba(13, 13, 13, 0.06)"
            }
        }
    },
    plugins: []
};
