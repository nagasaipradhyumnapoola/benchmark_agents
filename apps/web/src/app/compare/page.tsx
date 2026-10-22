import { Suspense } from "react";
import { Comparison } from "@/components/comparison";
import { Loading } from "@/components/common";
export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <Comparison />
    </Suspense>
  );
}
