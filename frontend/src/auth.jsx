import { useCallback, useEffect, useMemo, useState } from "react";
import { api, clearToken, getToken, setToken, setUnauthorizedHandler } from "./api.js";
import { AuthContext } from "./authContext.js";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // We only need to wait if a token is already stored and must be checked
  const [loading, setLoading] = useState(Boolean(getToken()));

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  // When the app opens: if a token is stored, ask the server who it belongs to
  useEffect(() => {
    if (!getToken()) return;
    api
      .me()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  // Any 401 from the API (for example an expired token) logs the user out
  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  const login = useCallback(async (email, password) => {
    const { access_token } = await api.login(email, password);
    setToken(access_token);
    try {
      setUser(await api.me());
    } catch (error) {
      clearToken();
      throw error;
    }
  }, []);

  const register = useCallback(
    async (email, password) => {
      await api.register(email, password);
      await login(email, password);
    },
    [login],
  );

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}