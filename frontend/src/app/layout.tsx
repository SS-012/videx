import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
	title: "Videx",
	description: "AI-assisted data annotation (ICL)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
	return (
		<html lang="en">
			<body>{children}</body>
		</html>
	);
}
