import type {
  Interview,
  InterviewReplyRequest,
  InterviewReplyResponseData,
  InterviewStartResponseData,
  InterviewStopRequest,
  Profile,
  SignInRequest,
  SignUpRequest,
} from "@/api";
import { AuthenticationApi, Configuration, InterviewApi, UserApi } from "@/api";
import { useQuery } from "@tanstack/vue-query";
import { isAxiosError } from "axios";
import { computed, toValue, type MaybeRefOrGetter } from "vue";
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

export const authApi = new AuthenticationApi(configuration);

export const userApi = new UserApi(configuration);

export const interviewApi = new InterviewApi(configuration);

export const queryKeys = {
  profile: () => ["user", "profile"] as const,
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

export const fetchInterviews = async () => {
  return withAuthenticatedRequest(async () => {
    return unwrapResponse(await userApi.apiUserInterviewsGet());
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

export const startInterview = async () => {
  return withAuthenticatedRequest(async () => {
    return unwrapResponse<InterviewStartResponseData>(await interviewApi.apiInterviewStartPost());
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

export const getProfileQueryOptions = () => ({
  queryKey: queryKeys.profile(),
  queryFn: fetchProfile,
});

export const getInterviewsQueryOptions = () => ({
  queryKey: queryKeys.interviews(),
  queryFn: fetchInterviews,
});

export function useProfileQuery(options?: { enabled?: MaybeRefOrGetter<boolean> }) {
  return useQuery({
    ...getProfileQueryOptions(),
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

export function useInterviews() {
  return useInterviewsQuery();
}

export type { Interview };
