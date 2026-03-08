---
name: fiber-v3
description: GoFiber v3 application development and v2-to-v3 migration guidance for Go services using `github.com/gofiber/fiber/v3`. Use when Codex needs to create new Fiber v3 handlers or apps, migrate Fiber v2 code, review a codebase for v3 compatibility, update middleware or client usage, or translate deprecated APIs such as `*fiber.Ctx`, `BodyParser`, `app.Static`, `app.Mount`, `ListenTLS`, or `fiber.AcquireAgent`.
---

# Fiber V3

## Classify the task

Start by deciding whether the work is:
- Building a new Fiber v3 service
- Migrating an existing Fiber v2 codebase
- Reviewing code for v3 compatibility or regressions

Check the baseline before editing:
- Use `github.com/gofiber/fiber/v3`
- Require Go `1.25` or later
- Expect handler signatures to use `fiber.Ctx`, not `*fiber.Ctx`

## Apply the migration workflow

Prefer this sequence for upgrades:

1. Run the Fiber CLI migrator when the user wants a broad automated upgrade.

   ```bash
   go install github.com/gofiber/cli/fiber@latest
   fiber migrate --to v3
   ```

2. Fix compile blockers first.
   - Update imports from `/v2` to `/v3`
   - Replace `*fiber.Ctx` with `fiber.Ctx`
   - Replace removed listen helpers with `app.Listen(..., fiber.ListenConfig{...})`
   - Replace parser APIs with `c.Bind().Body`, `c.Bind().Query`, `c.Bind().URI`, and `c.Bind().Cookie`

3. Fix routing and server behavior changes.
   - Replace `app.Static()` with `static.New(...)`
   - Replace `app.Mount()` with `app.Use()`
   - Review `app.Add()` callers because the signature changed
   - Review automatic `HEAD` route registration for `GET`
   - Review shutdown hooks because `OnShutdown` became `OnPreShutdown` and `OnPostShutdown`

4. Fix middleware and client migrations.
   - Replace string-key `c.Locals()` access for middleware state with the new `FromContext` helpers
   - Replace `KeyLookup`-style configs with extractor functions where required
   - Replace v2 `Agent` usage with the v3 `client.Client` / `Request` / `Response` model

5. Compile, run tests, and scan for lingering v2 APIs.

   ```bash
   rg -n 'fiber/v2|\*fiber\.Ctx|BodyParser|QueryParser|ParamsParser|CookieParser|RedirectToRoute|RedirectBack|app\.Static\(|app\.Mount\(|ListenTLS|ListenMutualTLS|EnableTrustedProxyCheck|TrustedProxies|KeyLookup|ContextKey|AcquireAgent|fiber\.(Get|Post|Put|Patch|Delete|Head)\('
   ```

## Load the right reference

- Read [references/migration-checklist.md](references/migration-checklist.md) for app, router, context, binding, redirect, and utils changes.
- Read [references/client-and-middlewares.md](references/client-and-middlewares.md) for the client package rewrite and middleware-specific migrations.
- Load only the file that matches the task. Avoid loading both unless the work spans both areas.

## Prefer native v3 code

- Prefer native Fiber v3 handlers over compatibility adapters when writing new code.
- Preserve prior behavior when defaults changed, especially for cache expiration, CSRF timeout, timeout middleware behavior, and automatic `HEAD` registration.
- Treat `RebuildTree()` as a specialized tool for dynamic route registration, not a default migration step.
- When middleware used to expose data through `c.Locals("...")`, switch to the package-specific accessor instead of inventing new string keys.
