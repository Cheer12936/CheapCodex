# Benchmark Results

This document summarizes a local synthetic benchmark used to test whether CheapCodex is useful in realistic Codex workflows.

The goal was not to prove that total tokens disappear. The goal was to test whether a cheap worker can reduce the amount of raw code Codex needs to read before making a verified edit.

## Test Fixture

A temporary full-stack project was generated under:

```text
%TEMP%\cheapcodex-complex-fixture
```

The fixture contained 41 files:

- `backend/src`: routes, controllers, services, models, middleware, utilities
- `frontend/src`: pages, API clients, state, hooks
- `tests`: backend and frontend tests
- `docs`: API and auth documentation
- `logs`: synthetic production logs
- `config`: environment examples

The fixture intentionally included:

- a cross-file authentication flow;
- stale auth documentation;
- token TTL and refresh behavior;
- test style examples;
- a refund calculation bug spanning route/controller/service/utility/frontend/tests/logs.

## Scenario Benchmarks

Live benchmarks used the configured DeepSeek worker. The `reduction` column estimates Codex-side context reduction by comparing rough raw input tokens with rough worker answer tokens.

| Scenario | Files | Raw Input Tokens | Worker Output Tokens | Reduction | Elapsed |
| --- | ---: | ---: | ---: | ---: | ---: |
| Project map | 26 | 25,093 | 539 | 97.9% | 10.582s |
| Login and refresh flow | 9 | 8,378 | 453 | 94.6% | 6.597s |
| Token TTL blast radius | 27 | 25,223 | 557 | 97.8% | 7.730s |
| Learn test style | 4 | 5,895 | 434 | 92.6% | 5.460s |
| Single tiny file control | 1 | 67 | not needed | 0.0% | not run |

## Trigger Behavior

The benchmark scenarios matched the current `AGENTS.md` worker rules:

- project map: unfamiliar repository and 3+ files;
- login flow: cross-file mapping and documentation alignment;
- token TTL change: blast-radius analysis before changing shared auth behavior;
- test style: learn existing tests before drafting new tests;
- single tiny file: should not trigger worker because the task is below the useful threshold.

## Live Bug-Fix Case Study

### Bug

The refund workflow spanned multiple files:

```text
RefundPage.jsx
  -> refundApi.createRefund()
  -> refundRoutes.js
  -> refundController.createRefund()
  -> refundService.refundOrder()
  -> money.calculateRefundCents()
```

The intentionally buggy function was:

```js
function calculateRefundCents(totalCents, refundPercent, shippingCents = 0) {
  const merchandiseCents = totalCents - shippingCents;
  const raw = merchandiseCents * (refundPercent / 100);
  return Math.round(raw * 100);
}
```

### Failure Reproduction

Before worker analysis:

```json
{"check":"calculateRefundCents","expected":6000,"actual":600000,"pass":false}
```

The expected result is 6,000 cents:

```text
totalCents = 12,500
shippingCents = 500
merchandiseCents = 12,000
50% refund = 6,000
```

The actual result was 600,000 cents, 100x too high.

### Worker Analysis

The worker was given 8 upstream/downstream files:

- `backend/src/routes/refundRoutes.js`
- `backend/src/controllers/refundController.js`
- `backend/src/services/refundService.js`
- `backend/src/utils/money.js`
- `frontend/src/api/refundApi.js`
- `frontend/src/pages/RefundPage.jsx`
- `tests/backend/refund.test.js`
- `logs/refund-error.log`

Worker usage:

```text
5715 input tokens / 189 output tokens
```

Worker result:

```text
Root cause:
calculateRefundCents computes raw in cents, then multiplies it by 100 again.

File:
backend/src/utils/money.js

Fix:
return Math.round(raw * 100)
-> return Math.round(raw)
```

### Codex Verification

Following the project rule, Codex did not edit based only on the worker summary. It verified the smallest relevant original files:

- `backend/src/utils/money.js`
- `tests/backend/refund.test.js`
- `logs/refund-error.log`

Evidence:

```text
test expected: 6000
log actual: 600000
code: return Math.round(raw * 100)
```

### Fix

Patch:

```diff
- return Math.round(raw * 100);
+ return Math.round(raw);
```

### Post-Fix Verification

Function-level verification:

```json
{"check":"calculateRefundCents","expected":6000,"actual":6000,"pass":true}
```

Service-level verification:

```json
{"check":"refundService.refundOrder","expected":6000,"actual":6000,"pass":true}
```

## Conclusion

CheapCodex is most useful for:

- cross-file function context analysis;
- logs + tests + source code triangulation;
- finding the smallest files Codex should inspect;
- reducing raw Codex context while preserving verification.

In the synthetic complex-project scenarios, worker summaries reduced Codex-side reading context by roughly 92% to 98%.

The important workflow is:

```text
worker reads broad context
Codex reads worker summary
Codex verifies the smallest relevant original files
Codex edits and runs checks
```

The worker is a scout, not the source of truth.

