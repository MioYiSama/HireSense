# Backend

## 认证

使用账号密码 + Access Token（JWT）进行认证

## 语音转文字

调用外部 Whisper.cpp 服务，然后传递给AI端

```shell
curl 127.0.0.1:8080/inference \
    -H "Content-Type: multipart/form-data" \
    -F file="@<file-path>" \
    -F response_format="verbose_json"
```

## 生成面试官回复

转发给AI端处理

默认编译就是 mock；要切到真实 AI，实现方式是 go build -tags interview_ai .

## 请求体上限

服务默认允许的请求体大小为 `64 MiB`。

如需覆盖，设置环境变量 `APP_BODY_LIMIT_BYTES`，例如 `107374182400` 表示 `100 GiB`。

当前语音上传链路会把整段音频读入内存后再转发给转写服务，所以把这个值设得非常大并不等于系统就能安全处理超大音频。
