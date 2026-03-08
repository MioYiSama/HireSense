# Fiber v3 migration checklist

## Table of contents

- Quick triage
- App and server changes
- Router and handler changes
- Context, binding, and redirect changes
- Defaults and behavior changes
- Search patterns

## Quick triage

- Require Go `1.25+`.
- Update imports from `github.com/gofiber/fiber/v2` to `github.com/gofiber/fiber/v3`.
- Expect handlers to use `func(c fiber.Ctx) error`, not `func(c *fiber.Ctx) error`.
- Use the CLI migrator for broad upgrades:

```bash
go install github.com/gofiber/cli/fiber@latest
fiber migrate --to v3
```

## App and server changes

- Replace removed listen helpers such as `ListenTLS`, `ListenMutualTLS`, and related variants with `app.Listen()` plus `fiber.ListenConfig`.
- Move old listen-related app config into `fiber.ListenConfig` when needed.
- Replace `EnableTrustedProxyCheck` with `TrustProxy`.
- Replace `TrustedProxies` with `TrustProxyConfig.Proxies`.
- Replace `OnShutdown` with `app.Hooks().OnPreShutdown(...)` or `app.Hooks().OnPostShutdown(...)`.
- Run `app.Listen()` in a goroutine if shutdown hooks must execute.

```go
app.Hooks().OnPostShutdown(func(err error) error {
    return nil
})
go app.Listen(":3000")
```

- Replace `app.Static()` with the static middleware:

```go
app.Get("/prefix*", static.New("./public"))
```

## Router and handler changes

- Replace `app.Mount("/api", subApp)` with `app.Use("/api", subApp)`.
- Review `app.Add()` because the signature changed from a single method string to `[]string` plus a required first handler.
- Prefer `RouteChain` only when the route-stack style is useful; `Route` keeps prefix encapsulation behavior.
- Review any `GET` route assumptions because Fiber now auto-registers a matching `HEAD` route unless `DisableHeadAutoRegister` is set.
- Use direct `net/http` handlers only as a migration bridge; prefer native Fiber handlers in hot paths.

## Context, binding, and redirect changes

- Replace `*fiber.Ctx` with `fiber.Ctx` everywhere.
- Replace parser APIs:
  - `c.BodyParser(&dst)` -> `c.Bind().Body(&dst)`
  - `c.QueryParser(&dst)` -> `c.Bind().Query(&dst)`
  - `c.ParamsParser(&dst)` -> `c.Bind().URI(&dst)`
  - `c.CookieParser(&dst)` -> `c.Bind().Cookie(&dst)`
- Rename struct tags for URI binding from `params:"id"` to `uri:"id"`.
- Treat `c.Bind()` as request binding. Use `c.ViewBind()` for view binding.
- Replace redirect helpers:
  - `c.RedirectToRoute("name")` -> `c.Redirect().Route("name")`
  - `c.RedirectBack()` -> `c.Redirect().Back()`
  - `c.Redirect("/new")` -> `c.Redirect().To("/new")`
- Replace `app.Test(req, timeout)` with `app.Test(req, fiber.TestConfig{...})`.

## Defaults and behavior changes

- Move the in-repo utils import to `github.com/gofiber/utils/v2`.
- Review cache defaults if the repo relied on v2 behavior:
  - `Expiration` default changed from `1 minute` to `5 minutes`
  - `MaxBytes` now defaults to `1 MB`
  - `Cache-Control` headers are emitted by default
- Review CSRF defaults:
  - `Expiration` became `IdleTimeout`
  - default timeout dropped from `1 hour` to `30 minutes`
  - `KeyLookup` was removed in favor of extractors
- Review timeout middleware carefully:
  - use `timeout.Config{Timeout: ...}`
  - handlers can observe timeout through `c.Context().Done()`
  - the middleware abandons work immediately on timeout

## Search patterns

Use these search terms to find common v2 leftovers:

```bash
rg -n 'fiber/v2|\*fiber\.Ctx|BodyParser|QueryParser|ParamsParser|CookieParser|RedirectToRoute|RedirectBack|app\.Static\(|app\.Mount\(|ListenTLS|ListenMutualTLS|EnableTrustedProxyCheck|TrustedProxies|timeout\.New\(|github\.com/gofiber/fiber/v2/utils'
```
