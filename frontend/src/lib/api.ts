import { useQuery } from "@tanstack/vue-query";
import { isAxiosError } from "axios";
import { computed, toValue, type MaybeRefOrGetter } from "vue";

import type {
  AddFavoriteQuestionRequest,
  FavoriteQuestion,
  Interview,
  InterviewReplyRequest,
  InterviewReplyResponseData,
  InterviewStartRequest,
  InterviewStartResponseData,
  InterviewStopRequest,
  Profile,
  ResumeAnalysis,
  SignInRequest,
  SignUpRequest,
} from "@/api";
import { AuthenticationApi, Configuration, InterviewApi, UserApi } from "@/api";
import { clearAll, getAccessToken, getUserInfo, setUserInfo } from "@/utils/token";

type ApiEnvelope<T> = {
  success: boolean;
  message: string;
  data: T;
};

const configuration = new Configuration({
  basePath: import.meta.env["VITE_BACKEND_URL"],
  accessToken: async () => {
    return getAccessToken();
  },
});

const resolveBackendUrl = (path: string) => {
  const basePath = import.meta.env["VITE_BACKEND_URL"] || window.location.origin;
  return new URL(path, basePath).toString();
};

export const authApi = new AuthenticationApi(configuration);

export const userApi = new UserApi(configuration);

export const interviewApi = new InterviewApi(configuration);

export const queryKeys = {
  favoriteQuestions: () => ["user", "favorite-questions"] as const,
  profile: () => ["user", "profile"] as const,
  resumeAnalysis: () => ["user", "resume-analysis"] as const,
  interviews: () => ["user", "interviews"] as const,
};

const syncStoredProfile = (profile: Profile) => {
  const currentUserInfo = getUserInfo();

  setUserInfo({
    ...currentUserInfo,
    name: profile.name,
    job: profile.job,
    resume: profile.resume ?? "",
    personalization: profile.personalization ?? "",
  });
};

const unwrapResponse = <T>(response: { data: ApiEnvelope<T> }) => {
  const payload = response.data;

  if (!payload.success) {
    throw new Error(payload.message || "请求失败");
  }

  return payload.data;
};

const withAuthenticatedRequest = async <T>(request: () => Promise<T>) => {
  try {
    return await request();
  } catch (error) {
    if (isAxiosError(error)) {
      const status = error.response?.status;
      if (status === 401 || status === 403) {
        clearAll();
      }
    }

    throw error;
  }
};

export const getApiErrorMessage = (
  error: unknown,
  fallbackMessage: string = "网络错误，请稍后重试",
) => {
  if (isAxiosError(error)) {
    const responseData = error.response?.data;
    if (
      responseData &&
      typeof responseData === "object" &&
      "message" in responseData &&
      typeof responseData.message === "string"
    ) {
      return responseData.message;
    }

    if (error.message) {
      return error.message;
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallbackMessage;
};

export const fetchProfile = async () => {
  return withAuthenticatedRequest(async () => {
    const profile = unwrapResponse(await userApi.apiUserProfileGet());
    syncStoredProfile(profile);
    return profile;
  });
};

export const fetchFavoriteQuestions = async () => {
  return withAuthenticatedRequest(async () => {
    return unwrapResponse<FavoriteQuestion[]>(await userApi.apiUserFavoriteQuestionsGet());
  });
};

export const fetchInterviews = async () => {
  return withAuthenticatedRequest(async () => {
    return unwrapResponse(await userApi.apiUserInterviewsGet());
  });
};

export const fetchResumeAnalysis = async () => {
  return withAuthenticatedRequest(async () => {
    const response = unwrapResponse(await userApi.apiUserResumeAnalysisGet());
    return response.analysis ?? null;
  });
};

export const signIn = async (request: SignInRequest) => {
  return unwrapResponse(await authApi.apiAuthSigninPost(request));
};

export const signUp = async (request: SignUpRequest) => {
  return unwrapResponse(await authApi.apiAuthSignupPost(request));
};

export const signOut = async () => {
  return withAuthenticatedRequest(async () => {
    return unwrapResponse(await authApi.apiAuthSignoutPost());
  });
};

export const updateProfile = async (profile: Profile) => {
  return withAuthenticatedRequest(async () => {
    unwrapResponse(await userApi.apiUserProfilePut(profile));
    return fetchProfile();
  });
};

export const addFavoriteQuestion = async (request: AddFavoriteQuestionRequest) => {
  return withAuthenticatedRequest(async () => {
    return unwrapResponse<FavoriteQuestion>(await userApi.apiUserFavoriteQuestionsPost(request));
  });
};

export const removeFavoriteQuestion = async (favoriteID: string) => {
  return withAuthenticatedRequest(async () => {
    return unwrapResponse(await userApi.apiUserFavoriteQuestionsFavoriteIDDelete(favoriteID));
  });
};

export const removeFavoriteQuestionSource = async ({
  interviewID,
  reviewIndex,
}: {
  interviewID: string;
  reviewIndex: number;
}) => {
  return withAuthenticatedRequest(async () => {
    return unwrapResponse(
      await userApi.apiUserFavoriteQuestionsSourceInterviewIDReviewIndexDelete(
        interviewID,
        reviewIndex,
      ),
    );
  });
};

export const generateResumeAnalysis = async () => {
  return withAuthenticatedRequest(async () => {
    return unwrapResponse<ResumeAnalysis>(await userApi.apiUserResumeAnalysisPost());
  });
};

export const startInterview = async (request?: InterviewStartRequest) => {
  return withAuthenticatedRequest(async () => {
    return unwrapResponse<InterviewStartResponseData>(
      await interviewApi.apiInterviewStartPost(request),
    );
  });
};

export const replyInterview = async ({
  id,
  payload,
  contentType,
}: {
  id: string;
  payload: InterviewReplyRequest | Blob;
  contentType?: string;
}) => {
  return withAuthenticatedRequest(async () => {
    return unwrapResponse<InterviewReplyResponseData>(
      await interviewApi.apiInterviewReplyPost(id, payload as InterviewReplyRequest, {
        headers: contentType ? { "Content-Type": contentType } : undefined,
      }),
    );
  });
};

export const stopInterview = async (request: InterviewStopRequest) => {
  return withAuthenticatedRequest(async () => {
    return unwrapResponse(await interviewApi.apiInterviewStopPost(request));
  });
};

export const synthesizeInterviewSpeech = async (text: string, signal?: AbortSignal) => {
  const token = getAccessToken();

  const response = await fetch(resolveBackendUrl("/api/interview/tts"), {
    method: "POST",
    headers: {
      Accept: "audio/mpeg",
      Authorization: token ? `Bearer ${token}` : "",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text }),
    signal,
  });

  if (response.status === 401 || response.status === 403) {
    clearAll();
  }

  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const payload = (await response.json()) as Partial<ApiEnvelope<null>>;
      throw new Error(payload.message || "请求失败");
    }

    throw new Error(`请求失败 (${response.status})`);
  }

  return response.blob();
};

export const getProfileQueryOptions = () => ({
  queryKey: queryKeys.profile(),
  queryFn: fetchProfile,
});

export const getFavoriteQuestionsQueryOptions = () => ({
  queryKey: queryKeys.favoriteQuestions(),
  queryFn: fetchFavoriteQuestions,
});

export const getInterviewsQueryOptions = () => ({
  queryKey: queryKeys.interviews(),
  queryFn: fetchInterviews,
});

export const getResumeAnalysisQueryOptions = () => ({
  queryKey: queryKeys.resumeAnalysis(),
  queryFn: fetchResumeAnalysis,
});

export function useProfileQuery(options?: { enabled?: MaybeRefOrGetter<boolean> }) {
  return useQuery({
    ...getProfileQueryOptions(),
    enabled: computed(() => {
      return Boolean(getAccessToken()) && Boolean(toValue(options?.enabled ?? true));
    }),
  });
}

export function useFavoriteQuestionsQuery(options?: { enabled?: MaybeRefOrGetter<boolean> }) {
  return useQuery({
    ...getFavoriteQuestionsQueryOptions(),
    enabled: computed(() => {
      return Boolean(getAccessToken()) && Boolean(toValue(options?.enabled ?? true));
    }),
  });
}

export function useInterviewsQuery(options?: { enabled?: MaybeRefOrGetter<boolean> }) {
  return useQuery({
    ...getInterviewsQueryOptions(),
    enabled: computed(() => {
      return Boolean(getAccessToken()) && Boolean(toValue(options?.enabled ?? true));
    }),
  });
}

export function useResumeAnalysisQuery(options?: { enabled?: MaybeRefOrGetter<boolean> }) {
  return useQuery({
    ...getResumeAnalysisQueryOptions(),
    enabled: computed(() => {
      return Boolean(getAccessToken()) && Boolean(toValue(options?.enabled ?? true));
    }),
  });
}

export function useInterviews() {
  return useInterviewsQuery();
}

export type { FavoriteQuestion, Interview, ResumeAnalysis };
