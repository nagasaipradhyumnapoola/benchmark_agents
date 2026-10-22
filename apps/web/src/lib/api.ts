import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
export async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    `/api${path}`,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      message =
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail ?? data);
    } catch {}
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
export function useApi<T>(path: string, poll = false, enabled = true) {
  return useQuery({
    queryKey: [path],
    queryFn: () => request<T>(path),
    enabled,
    retry: 1,
    refetchInterval: poll
      ? (query) => {
          const data = query.state.data;
          if (
            data &&
            typeof data === "object" &&
            "status" in data &&
            typeof data.status === "string"
          ) {
            return active(data.status) ? 2000 : false;
          }
          return 2000;
        }
      : false,
  });
}
export function useAction<T = unknown>(
  path: string,
  onSuccess?: (data: T) => void,
) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: unknown) => request<T>(path, body),
    onSuccess: (data) => {
      void client.invalidateQueries();
      onSuccess?.(data);
    },
  });
}
export const active = (status: string) =>
  ["queued", "running"].includes(status);
export const format = (value: unknown, digits = 2) =>
  typeof value === "number"
    ? value.toLocaleString(undefined, { maximumFractionDigits: digits })
    : "Unavailable";
export const percent = (value: unknown) =>
  typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "Unavailable";
