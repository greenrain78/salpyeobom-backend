"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, apiRequest, clearToken, getToken, setToken } from "./api";
import type { TokenResponse, UserOut } from "./types";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: UserOut | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const ME_QUERY_KEY = ["auth", "me"] as const;

// 다른 탭이 토큰을 바꾸면 자동 반영되도록 storage 이벤트 구독.
function subscribeToken(callback: () => void) {
  if (typeof window === "undefined") return () => {};
  const handler = (e: StorageEvent) => {
    if (e.key === null || e.key === "salpyeobom_token") callback();
  };
  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}

const getTokenSnapshot = () => getToken();
const getServerSnapshot = () => null;

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  // SSR-safe: 서버 렌더 시에는 null, 클라이언트에서는 localStorage 값.
  // useState + useEffect 안티패턴을 피하기 위해 useSyncExternalStore 사용.
  const token = useSyncExternalStore(subscribeToken, getTokenSnapshot, getServerSnapshot);
  const hasToken = token !== null;

  const meQuery = useQuery<UserOut, ApiError>({
    queryKey: ME_QUERY_KEY,
    queryFn: async () => {
      try {
        return await apiRequest<UserOut>("/api/v1/auth/me");
      } catch (err) {
        // 401 은 토큰이 유효하지 않은 것이므로 즉시 정리. 다른 에러(네트워크/5xx)
        // 에는 토큰을 유지해 사용자가 재시도하면 회복할 수 있게 한다.
        if (err instanceof ApiError && err.status === 401) {
          clearToken();
        }
        throw err;
      }
    },
    enabled: hasToken,
    retry: (failureCount, err) => {
      if (err instanceof ApiError && err.status === 401) return false;
      return failureCount < 1;
    },
    staleTime: 5 * 60_000,
  });

  const status: AuthStatus = (() => {
    if (!hasToken) return "unauthenticated";
    if (meQuery.isSuccess) return "authenticated";
    if (
      meQuery.isError &&
      meQuery.error instanceof ApiError &&
      meQuery.error.status === 401
    ) {
      return "unauthenticated";
    }
    return "loading";
  })();

  const user = meQuery.data ?? null;

  const login = useCallback(
    async (username: string, password: string) => {
      const res = await apiRequest<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        auth: false,
        body: { username, password },
      });
      setToken(res.access_token);
      // setToken 은 storage 이벤트를 같은 창에서 발생시키지 않으므로,
      // query 를 직접 invalidate + refetch 하여 즉시 /me 를 가져온다.
      await queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY });
      await queryClient.refetchQueries({ queryKey: ME_QUERY_KEY });
    },
    [queryClient]
  );

  const logout = useCallback(() => {
    clearToken();
    queryClient.clear();
    router.push("/login");
  }, [queryClient, router]);

  const refresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY });
  }, [queryClient]);

  const value = useMemo(
    () => ({ status, user, login, logout, refresh }),
    [status, user, login, logout, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
