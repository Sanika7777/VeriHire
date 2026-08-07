import type { Metadata } from "next";
import { Suspense } from "react";

import { SearchPageContent } from "./search-page-content";

export const metadata: Metadata = {
  title: "Search",
  description: "Search VeriHire for a recruiter, company or job posting.",
};

export default function SearchPage() {
  return (
    <Suspense fallback={null}>
      <SearchPageContent />
    </Suspense>
  );
}
