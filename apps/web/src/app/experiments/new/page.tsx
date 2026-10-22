import { Suspense } from "react";
import { Builder } from "@/components/builder";
import { Loading } from "@/components/common";
export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <Builder />
    </Suspense>
  );
}
