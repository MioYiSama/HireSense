const ACCESS_TOKEN_KEY = "ACCESS_TOKEN";
const USER_INFO_KEY = "USER_INFO";

export function getAccessToken(): string {
  return localStorage.getItem(ACCESS_TOKEN_KEY) ?? "";
}

export function setAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function removeAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}

export function getUserInfo(): any {
  const userInfo = localStorage.getItem(USER_INFO_KEY);
  return userInfo ? JSON.parse(userInfo) : null;
}

export function setUserInfo(userInfo: any): void {
  localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo));
}

export function removeUserInfo(): void {
  localStorage.removeItem(USER_INFO_KEY);
}

export function clearAll(): void {
  removeAccessToken();
  removeUserInfo();
}
