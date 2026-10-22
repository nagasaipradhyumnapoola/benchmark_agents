import { Suspense } from "react";
import { Overview } from "@/components/overview";
export default function Page() {
  return (
    <Suspense>
      <Overview />
    </Suspense>
  );
}
