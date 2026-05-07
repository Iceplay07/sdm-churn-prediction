import { useQuery } from "@tanstack/react-query";
import { api } from "./client.js";
import { mockAtRisk, mockClient, mockTransactions, mockInfo } from "../lib/mock.js";

const USE_MOCK = window.__SDM_USE_MOCK__ === true;

async function safeGet(path, params, fallback) {
  if (USE_MOCK) return fallback();
  try {
    const { data } = await api.get(path, { params });
    return data;
  } catch (e) {
    if (window.__SDM_FALLBACK_ON_ERROR__) {
      console.warn(`[api] ${path} failed, using mock`, e?.message);
      return fallback();
    }
    throw e;
  }
}

export function useInfo() {
  return useQuery({
    queryKey: ["info"],
    queryFn: () => safeGet("/info", undefined, mockInfo),
    staleTime: 5 * 60_000,
  });
}

export function useAtRisk(params) {
  return useQuery({
    queryKey: ["at-risk", params],
    queryFn: () => safeGet("/clients/at-risk", params, () => mockAtRisk(params)),
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  });
}

export function useClient(clientId) {
  return useQuery({
    queryKey: ["client", clientId],
    queryFn: () => safeGet(`/clients/${clientId}`, undefined, () => mockClient(clientId)),
    enabled: clientId != null,
  });
}

export function useTransactions(clientId, nDays = 90) {
  return useQuery({
    queryKey: ["tx", clientId, nDays],
    queryFn: () => safeGet(`/clients/${clientId}/transactions`, { n_days: nDays }, () => mockTransactions(clientId, nDays)),
    enabled: clientId != null,
    staleTime: 5 * 60_000,
  });
}
