import "./globals.css";

import type { Metadata } from "next";
import { ReactNode } from "react";


export const metadata: Metadata = {
  title: "Budget Tracker",
  description: "Professionalized budget tracker with a Flask backend and Next.js frontend.",
};


export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

