import { Suspense } from "react";
import { Reports } from "@/components/reports";
import { Loading } from "@/components/common";
export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <Reports />
    </Suspense>
  );
}
