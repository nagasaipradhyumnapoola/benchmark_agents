import { Suspense } from "react";
import { Experiments } from "@/components/experiments";
import { Loading } from "@/components/common";
export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <Experiments />
    </Suspense>
  );
}
