import { Suspense } from "react";
import { Settings } from "@/components/settings";
import { Loading } from "@/components/common";
export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <Settings />
    </Suspense>
  );
}
