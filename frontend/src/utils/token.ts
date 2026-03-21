const ACCESS_TOKEN_KEY = "ACCESS_TOKEN";
const USER_INFO_KEY = "USER_INFO";
const INTERVIEW_ID_KEY = "INTERVIEW_ID";
const INITIAL_REPLY_KEY = "INITIAL_REPLY";

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

export function getInterviewId(): string {
  return localStorage.getItem(INTERVIEW_ID_KEY) ?? "";
}

export function setInterviewId(interviewId: string): void {
  localStorage.setItem(INTERVIEW_ID_KEY, interviewId);
}

export function removeInterviewId(): void {
  localStorage.removeItem(INTERVIEW_ID_KEY);
}

export function getInitialReply(): string {
  return localStorage.getItem(INITIAL_REPLY_KEY) ?? "";
}

export function setInitialReply(reply: string): void {
  localStorage.setItem(INITIAL_REPLY_KEY, reply);
}

export function removeInitialReply(): void {
  localStorage.removeItem(INITIAL_REPLY_KEY);
}

export function clearAll(): void {
  removeAccessToken();
  removeUserInfo();
  removeInterviewId();
  removeInitialReply();
}
