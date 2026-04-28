import { Inter } from "next/font/google";
import { AuthProvider } from "@/context/AuthContext";
import "./globals.css";
const inter = Inter({
    subsets: ["latin"],
    variable: "--font-inter",
});
export const metadata = {
    title: {
        default: "Order Papers System",
        template: "%s | Order Papers System",
    },
    description: "Internal parliamentary document management and similarity retrieval portal for the National Assembly of Zambia.",
};
export default function RootLayout({ children }) {
    return (<html lang="en">
      <body className={`${inter.variable} bg-[--bg] font-sans text-sm text-[--black] antialiased`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>);
}
