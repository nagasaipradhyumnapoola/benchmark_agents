import { Suspense } from "react";
import { Documentation } from "@/components/documentation";
import { Loading } from "@/components/common";
export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <Documentation />
    </Suspense>
  );
}
