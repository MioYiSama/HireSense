# Fiber v3 client and middleware migration

## Table of contents

- Client package model
- Common client rewrites
- Middleware data access
- Middleware-specific config changes
- Search patterns

## Client package model

- Update imports from `github.com/gofiber/fiber/v2/client` to `github.com/gofiber/fiber/v3/client`.
- Replace the v2 `Agent` model with:
  - `client.Client` for reusable defaults
  - `client.Request` for one request
  - `client.Response` for typed results
- Replace tuple responses like `(code, body, errs)` with `(*client.Response, error)`.
- Close responses after use.

## Common client rewrites

- Replace `fiber.Get(...)`, `fiber.Post(...)`, and similar top-level helpers with `client.Get(...)`, `client.Post(...)`, or a reusable `client.New()` instance.
- Replace `fiber.AcquireAgent()` patterns with a long-lived `client.Client`, or with `client.AcquireRequest()` / `client.AcquireResponse()` when explicit pooling is required.
- Replace request decoding patterns:
  - `Agent.Struct(&dst)` -> `resp.JSON(&dst)` or `resp.XML(&dst)`
  - `Agent.Bytes()` / `Agent.String()` -> `resp.Body()` / `resp.String()`
- Replace manual URL formatting with `PathParam` and `Param` in `client.Config` when possible.

```go
cli := client.New().SetBaseURL("https://api.example.com")
resp, err := cli.Get("/users/:id", client.Config{
    PathParam: map[string]string{"id": id},
    Param:     map[string]string{"active": "true"},
})
if err != nil {
    return err
}
defer resp.Close()
```

## Middleware data access

Do not keep reading middleware state through string keys in `c.Locals("...")`. Use the package-specific accessors instead:

- `requestid.FromContext(c)`
- `csrf.TokenFromContext(c)`
- `csrf.HandlerFromContext(c)`
- `session.FromContext(c)`
- `basicauth.UsernameFromContext(c)`
- `keyauth.TokenFromContext(c)`

This change applies to Fiber-provided middleware data, not to arbitrary application values you store in `c.Locals()` yourself.

## Middleware-specific config changes

- `basicauth`:
  - Change `Authorizer` to `func(user, pass string, c fiber.Ctx) bool`
  - Store configured passwords as hashes, not plaintext
- `keyauth`:
  - Replace `KeyLookup` with `Extractor`
  - Replace manual bearer parsing with helpers such as `keyauth.FromAuthHeader(...)`
- `session`:
  - `session.New()` now returns a middleware handler
  - create stores with `session.NewStore()` when you need explicit store access
  - release sessions obtained from a store with `sess.Release()`
  - replace `KeyLookup` with extractors such as `session.FromCookie(...)`
- `cors`:
  - convert `AllowOrigins`, `AllowMethods`, `AllowHeaders`, and `ExposeHeaders` from comma-separated strings to slices
- `csrf`:
  - rename `Expiration` to `IdleTimeout`
  - replace `KeyLookup` with `Extractor`
  - do not use `csrf.FromCookie`, which was removed
- `timeout`:
  - replace `timeout.New(handler, 2*time.Second)` with `timeout.New(handler, timeout.Config{Timeout: 2 * time.Second})`
- `filesystem`:
  - replace it with `static.New(...)`
- `monitor`:
  - move imports to `github.com/gofiber/contrib/monitor`
- `healthcheck`:
  - register liveness, readiness, and startup handlers separately
- `proxy`:
  - move TLS settings into the client via `proxy.WithClient(&fasthttp.Client{TLSConfig: ...})`

## Search patterns

Use these search terms to find common client and middleware leftovers:

```bash
rg -n 'fiber\\.AcquireAgent|fiber\\.(Get|Post|Put|Patch|Delete|Head)\\(|KeyLookup|ContextKey|Locals\\(\"requestid\"|Locals\\(\"csrf|Locals\\(\"session|Authorizer: func\\(user, pass string\\)|timeout\\.New\\(|middleware/filesystem|middleware/monitor|proxy\\.WithTlsConfig'
```
