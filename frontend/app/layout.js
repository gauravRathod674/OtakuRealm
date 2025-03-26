import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "OtakuRealm",
  description:
    "OtakuRealm is an anime streaming and manga reading site with many features like chatbot.",
};

// Server-side function to fetch homepage data and extract footer data.
async function getFooterData() {
  // Use the built‑in fetch API on the server.
  // The 'cache: "no-store"' option forces a fresh fetch.
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/`, {
    cache: "no-store",
  });
  const data = await res.json();
  return data.footer;
}

export default async function RootLayout({ children }) {
  // Fetch footer data on the server.
  const footerData = await getFooterData();

  return (
    <html lang="en">
      <head>
        <link
          href="https://unpkg.com/boxicons@2.1.4/css/boxicons.min.css"
          rel="stylesheet"
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Navbar />
        {children}
        {/* Pass the fetched footer data */}
        <Footer footerData={footerData} />
        <script src="https://code.jquery.com/jquery-3.6.4.min.js"></script>
      </body>
    </html>
  );
}
