export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("token", token);
}

export function removeToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
}

export function isAuthenticated(): boolean {
  const token = getToken();
  if (!token) return false;

  try {
    const parts = token.split(".");
    if (parts.length !== 3) return false;

    // Decode JWT payload
    const payload = JSON.parse(window.atob(parts[1]));
    const exp = payload.exp;
    
    // Check expiration (exp is in epoch seconds, Date.now() in ms)
    if (exp && Date.now() >= exp * 1000) {
      removeToken();
      return false;
    }
    
    return true;
  } catch (e) {
    return false;
  }
}
