import { Suspense } from "react";
import { Optimize } from "@/components/optimize";
import { Loading } from "@/components/common";
export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <Optimize />
    </Suspense>
  );
}
