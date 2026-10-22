import { Suspense } from "react";
import { Benchmarks } from "@/components/benchmarks";
import { Loading } from "@/components/common";
export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <Benchmarks />
    </Suspense>
  );
}
