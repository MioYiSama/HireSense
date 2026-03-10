import { AuthenticationApi, Configuration, InterviewApi, UserApi } from "@/api";
import { useQuery } from "@tanstack/vue-query";
import { getAccessToken } from "@/utils/token";

const configuration = new Configuration({
  basePath: "http://127.0.0.1:8080",
  accessToken: async () => {
    return getAccessToken();
  },
});

export const authApi = new AuthenticationApi(configuration);

export const userApi = new UserApi(configuration);

export const interviewApi = new InterviewApi(configuration);

export function useInterviews() {
  return useQuery({
    queryKey: ["interviews"],
    queryFn: async () => userApi.apiUserInterviewsGet(),
  });
}
