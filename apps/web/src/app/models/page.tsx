import { Suspense } from "react";
import { Registry } from "@/components/registry";
import { Loading } from "@/components/common";
export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <Registry kind="models" />
    </Suspense>
  );
}
