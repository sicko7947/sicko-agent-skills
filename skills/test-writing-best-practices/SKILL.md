---
name: test-writing-best-practices
description: Use when writing, fixing, refactoring, or reviewing tests in this repo or similar TypeScript apps. Covers Vitest, React Testing Library, TypeScript test typecheck, typed fixtures, mocking strategy, warning cleanup, and validation workflow for web and API tests.
---

# Test Writing Best Practices

Use this skill when adding or fixing tests. The goal is not just "make tests pass" — it is:
- preserve product behavior
- keep tests readable and user-centered
- keep tests type-safe
- fix repeated patterns centrally
- leave `check`, `check:test`, `test`, and `lint` green

## Source-aligned principles

These recommendations align with current official guidance:
- React recommends `await act(async () => ...)` for updates that cross async boundaries.
- Testing Library recommends testing through the DOM the way users use the UI.
- Testing Library recommends `user-event` over low-level `fireEvent` for realistic interactions when possible.
- Vitest mock APIs are intentionally typed to the original return type; if your mock shape diverges, prefer typed fixtures or partial helpers over scattered `any`.
- TypeScript should typecheck tests too; do not treat test files as a type-safety blind spot.

## Default workflow

1. Run the app-specific test typecheck first.
2. Fix shared setup/helpers before leaf tests.
3. Group failures by pattern, not file order.
4. Prefer typed fixtures/builders over inline object literals.
5. Only use broad escapes in one shared helper, not repeated per test file.
6. Re-run focused tests after each cluster.
7. Finish with full validation.

## Validation order

### `apps/web`
- `bun run check:test`
- `bun run check`
- `bun run test`
- `bun run lint`

### `apps/api`
- `bun run check:test`
- `bun run check`
- `bun test`
- `bun run lint`

If one of these is missing, add the minimal config/scripts needed rather than skipping the gate.

## Web testing rules

### React + Testing Library
- Prefer `screen.getByRole`, `getByLabelText`, and other semantic queries.
- Use `user-event` for realistic interactions when practical.
- Use `fireEvent` only when the interaction is intentionally low-level or `user-event` is not a good fit.
- Avoid asserting internal implementation details or component instances.
- Avoid brittle `container.querySelector(...)` unless there is no meaningful accessible query.

### `act(...)`
- If a test triggers async state changes, use `await act(async () => ...)`.
- If React Testing Library helpers already wrap the interaction, do not double-wrap unless warnings prove it is needed.
- If warnings are widespread, fix the specific interaction pattern rather than silencing globally.

### UI smoke tests
- A simple "renders without throwing" test is acceptable for tiny wrappers, but add at least one meaningful assertion about visible output, accessibility, or behavior.
- Do not create nested-button test fixtures with Radix triggers. Use `asChild` where appropriate or pass plain text when the trigger itself renders a button.

## Type safety rules

### Test files should be typechecked
- Keep a dedicated `tsconfig.test.json` when the production config excludes tests.
- Include test-only declarations narrowly under test scope.
- Avoid excluding failing tests from typecheck.

### Prefer typed fixtures
Create shared builders for repeated domain objects:
- `makeUser()`
- `makeSession()`
- `makeProject()`
- `makeTender()` / `makeGrant()`
- file/folder fixtures
- billing/notification/dashboard fixtures

Fixture builders should:
- provide a complete valid default shape
- accept `Partial<T>` overrides
- live in shared test helpers
- be reused instead of copy-pasted inline literals

### Mocking hierarchy
Prefer this order:
1. real value with small overrides
2. typed fixture builder
3. Vitest partial/deep mocked helper
4. centralized escape hatch
5. file-local `as any` only as a last resort

Bad:
- `const mocked = vi.mocked as any` repeated across many files
- ad-hoc partial object literals pretending to be full domain types

Better:
- shared fixture builders
- a single shared helper for unavoidable mock typing friction
- explicit comments if a test-only escape hatch is truly required

## Vitest mocking rules

- Clear or reset mocks between tests.
- Prefer `vi.spyOn` for existing objects when you care about original shape.
- Prefer `vi.mock` at module boundaries.
- Keep mock return values aligned with the real function contract.
- If you need only part of a large return shape, use a fixture builder and override only what the scenario needs.
- For async mocks, return the real contract shape, not a minimal ad-hoc shape, unless a shared helper intentionally widens it.

## API test rules

- Test behavior and contract boundaries, not framework internals.
- Keep service and handler tests explicit about success, failure, and edge cases.
- Prefer stable typed mocks in `src/test/setup/` or equivalent shared helpers.
- Narrow unions explicitly instead of assuming the success branch.
- Add test-only declarations only when library typings truly block correct tests.

## Warning cleanup guidance

Warnings that should usually be fixed:
- React `act(...)` warnings caused by test interactions
- nested interactive element warnings created by test fixtures
- repeated setup warnings that can be solved centrally

Warnings that may be acceptable if intentional and non-failing:
- explicit error-path logs from tests validating failures
- environment limitations that do not affect correctness, if fully isolated and understood

Do not destabilize green tests just to eliminate every warning. Prefer low-risk cleanup.

## Repo-specific guidance

### Imports
- Use `@/` imports for app source imports.
- Avoid parent-relative imports for app code.

### `apps/web`
- Prefer shared fixtures in `src/__tests__/helpers/`.
- Keep setup-only globals/stubs in `src/__tests__/setup.ts`.
- Keep test-only type shims in `src/__tests__/types/`.

### `apps/api`
- Prefer shared test setup under `src/test/setup/`.
- If Bun/Vitest typing gaps exist, centralize them in setup or declarations rather than scattering casts.

## When you must stop and refactor centrally

Stop fixing leaf tests one-by-one if you see repeated failures from:
- the same missing mock fields
- the same stale fixture shape
- the same module mock typing issue
- cross-test module cache contamination
- setup/global environment gaps

Create or improve a helper first, then resume the leaf tests.

## What "done" means

A test task is done only when:
- behavior is unchanged unless a real bug was fixed
- tests are readable and reasonably user-centered
- test typecheck passes
- production typecheck passes
- test suite passes
- lint passes
- repeated unsafe patterns were reduced, not spread further

## Preferred response pattern when applying this skill

When asked to write or fix tests:
- state the validation gates you will satisfy
- inspect existing setup/helpers first
- fix central issues before leaf suites
- add or reuse typed fixtures
- keep final changes minimal and focused
