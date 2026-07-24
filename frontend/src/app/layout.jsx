import { AuthProvider } from "@/context/AuthContext";
import "./globals.css";
export const metadata = {
    title: {
        default: "Order Papers System",
        template: "%s | Order Papers System",
    },
    description: "Internal parliamentary document management and similarity retrieval portal for the National Assembly of Zambia.",
};
export default function RootLayout({ children }) {
    return (<html lang="en">
      <body className="app-body">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>);
}
