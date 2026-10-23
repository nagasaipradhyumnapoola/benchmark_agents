import { Suspense } from "react";
import { AgentHub } from "@/components/agent-hub";
import { Loading } from "@/components/common";

export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <AgentHub />
    </Suspense>
  );
}
