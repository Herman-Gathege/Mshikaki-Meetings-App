import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";

export type Health = { status: string; version: string };
export type Readiness = { status: string; database: string; reason?: string };

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<Health>("/health"),
    refetchInterval: 30_000,
  });
}

export function useReadiness() {
  return useQuery({
    queryKey: ["health", "ready"],
    queryFn: () => apiFetch<Readiness>("/health/ready"),
    refetchInterval: 30_000,
  });
}
