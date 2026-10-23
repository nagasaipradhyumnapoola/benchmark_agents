import { Suspense } from "react";
import { Community } from "@/components/community";
import { Loading } from "@/components/common";

export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <Community />
    </Suspense>
  );
}
