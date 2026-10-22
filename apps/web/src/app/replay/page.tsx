import { Suspense } from "react";
import { Replay } from "@/components/replay";
import { Loading } from "@/components/common";
export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <Replay />
    </Suspense>
  );
}
