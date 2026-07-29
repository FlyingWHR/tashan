# tashan — payments & seller payouts (decision)

> Research date 2026-07-25. **Headline: Polar.sh cannot run the creator marketplace.** It's an excellent
> single-organization Merchant-of-Record, but it has **no multi-seller / connected-account / revenue-split
> primitive** — so it cannot pay out third-party creators. The marketplace payout leg needs **Stripe
> Connect**. Use **both**: Stripe Connect for creators-selling-via-tashan, Polar for tashan-selling-tashan.

## The finding that changes the plan

tashan's model is: *creators list, buyers pay, the creator keeps the lion's share, tashan takes a thin
**flat** cut, and the ranking is never for sale.* That's a **marketplace with third-party payouts**.

- **Polar.sh is single-org only.** You sell *your* products; there is no marketplace, connected account,
  sub-organization, "sell on behalf of others," or revenue split. Every seller would need their own Polar
  account, and Polar won't route/split a payout to an external creator. Polar's own "payouts" = the org
  owner withdrawing *its own* balance. → **Polar cannot be the payment platform for the creator
  marketplace.** (It's still the *best* tool for tashan's own first-party revenue — see below.)
- **Stripe Connect is the standard for exactly this.** Express/Custom connected accounts + destination
  charges route funds to the creator; tashan's cut is set with **`application_fee_amount` — a fixed integer
  in cents, i.e. a native FLAT cut, not a percentage toll.** That maps *perfectly* onto the thin-flat-cut
  firewall (payment flow never touches the score). Stripe's hosted Express onboarding runs each creator's
  KYC for you.

## The 2026 fork you must pick a side of

No platform gives you **both** Merchant-of-Record (tax handled for you) **and** Connect-style third-party
payouts on your *own* branded surface:

| | Merchant-of-Record (tax handled) | Multi-seller payouts to 3rd-party creators |
|---|---|---|
| Polar / Lemon Squeezy / Paddle / Stripe Managed Payments | ✅ | ❌ first-party only |
| **Stripe Connect** | ❌ (tashan owns tax) | ✅ **the standard** |
| **Whop** | ✅ optional (+0.5%) | ✅ but on *Whop's* marketplace/branding |
| x402 / USDC (Coinbase) | ❌ | ✅ instant/global, crypto-native, tiny volume |

(Stripe explicitly walls its **Managed Payments** MoR off from **Connect** — you cannot combine MoR + Connect on Stripe.)

## Recommended architecture

1. **Creator marketplace (buyer charge + creator payout + tashan's cut): Stripe Connect**, Express accounts,
   **destination charges** with a fixed `application_fee_amount` (the flat cut). Stripe runs creator KYC.
2. **tashan's OWN revenue (Pro plans, API, the "rendering/delivery" service): Polar.sh.** This is exactly
   what Polar is best at — MoR handles *tashan's* global VAT/GST/sales-tax, plus usage-metered billing for
   the delivery service. Clean separation: *tashan selling tashan* = Polar; *creators selling via tashan* = Stripe Connect.
3. **x402/USDC: a later, complementary rail** for agent-to-agent metered delivery / crypto-native creators — not the launch payout system.
4. **Turnkey fallback:** if the founder would rather not own tax + build the payout plumbing, **Whop** does
   MoR + creator payouts in one — at the cost of ceding branding/UX (it's Whop's marketplace). Good buy-vs-build reference.

## What tashan builds (on Cloudflare)

- **Worker endpoints:** `POST /checkout` (Stripe Checkout/PaymentIntent with destination + `application_fee_amount`);
  `POST /connect/onboard` (create/refresh Express account + onboarding link); `POST /webhooks/stripe` (verify
  signature; handle `payment_intent.succeeded` / `charge.refunded` / `account.updated` / `payout.*`; on success
  mint the entitlement/license key + unlock the deliverable). Call Stripe's REST API directly from the Worker
  (the Node SDK isn't Workers-native).
- **D1 tables:** `sellers` (stripe_account_id, onboarding_status, country), `listings` (seller_id, price,
  deliverable_ref), `orders` (buyer, listing_id, amount, application_fee, transfer_id, status),
  `payout_ledger`, `entitlements`/`license_keys`. **Kept physically separate from `capabilities`** so the
  scorer can never join commerce — enforced by `tests/test_firewall.py`.
- **R2:** the actual digital deliverable / license artifacts; sign time-limited download URLs on the paid-order webhook.
- **CSP:** a **scoped** `/checkout` policy adds `js.stripe.com` (script/frame) + `api.stripe.com` (connect);
  the strict `default-src 'self'` stays everywhere else.

## Needs the founder personally (not buildable unattended)

- A **tashan business entity** + a **Stripe platform account** (platform-level KYC/underwriting).
- **Sales-tax registration & remittance** — because Connect is **not** MoR, tashan owes tax where it has
  nexus: EU VAT/OSS, UK VAT, US state economic-nexus. Stripe Tax *calculates*; registration/filing is the
  founder's job. **This is the single biggest cost of choosing Connect over an MoR** — weigh vs Whop's turnkey MoR-marketplace.
- Each **creator completes Stripe Express KYC** and must be in a Stripe-supported payout country.
- **Verify before committing:** Stripe Express connected-account **country coverage** vs tashan's actual
  creator geography (gaps in parts of Africa / South Asia / LatAm). If many creators fall outside it, that's
  where x402/USDC or Whop re-enters.

## Fees (for the model)
Stripe Connect: 2.9% + 30¢ processing + 0.25% + $0.25/payout + $2/mo per active connected account.
Polar (tashan's first-party): 3.4–5% + 30–50¢ by plan (grandfathered 4% + 40¢), +1.5% intl, $15/dispute.

Sources: Polar MoR/fees/payouts docs · Stripe Connect (`application_fee_amount`, pricing, Managed-Payments-vs-Connect
limit) · Lemon Squeezy / Paddle / Gumroad / Whop MoR docs · Coinbase x402. (Full URLs in the research transcript.)

---

## Polar webhook — how it is wired (implemented 2026-07-29)

`functions/api/polar.js` is the receiver, `functions/api/polar.test.mjs` is the security test (in the
suite). Polar follows the [Standard Webhooks](https://standardwebhooks.com) spec.

**In the Polar dashboard** — organization settings → Webhooks → *Add Endpoint*:

| field | value |
|---|---|
| URL | `https://tashan.sh/api/polar` |
| Format | **Raw** (not Discord/Slack) |
| Secret | generate one, then copy it — this is **not** the API key |
| Events | `subscription.*` + `order.paid` + `order.refunded` (the set `polar.js` acts on) |

**Then give the Worker the secret** (never commit it — it is not an env var in `wrangler.toml`, it is a
secret):

```sh
npx wrangler@3 pages secret put POLAR_WEBHOOK_SECRET --project-name tashan
# paste the signing secret from the dashboard
```

To record entitlement, bind a KV namespace as `TASHAN_KV` (Pages → Settings → Bindings). Until it is
bound the endpoint verifies and 200s but stores nothing, exactly like `TASHAN_AE` in `e.js` — a missing
binding must not 5xx, because **Polar disables an endpoint after 10 consecutive non-2xx responses.**

### Three things that bite

1. **The secret is base64.** The HMAC key is the *decoded bytes*, not the ASCII of the string you copied.
   The SDKs hide this; we have no SDK, so `polar.js` decodes explicitly. Getting it wrong fails closed —
   every delivery 403s, which looks identical to a wrong secret. `polar.test.mjs` pins this case.
2. **The raw body must be hashed, not re-serialised JSON.** `JSON.parse` → `JSON.stringify` changes key
   order, whitespace and unicode escapes, and the signature never matches again. `polar.js` reads
   `await request.text()` once and signs that.
3. **The route must stay public.** Polar does not follow redirects and never authenticates, so the
   endpoint cannot sit behind any auth middleware. Its own signature check *is* the auth.

The API key you already hold is for *calling* Polar (creating checkouts, reading subscriptions) and is a
different credential from the webhook signing secret. It is not needed by this endpoint.

### What this does NOT yet do

Verification and entitlement recording are real. There is still **no auth, no accounts and no session**,
so nothing on the site reads `ent:<email>` yet — a paid feature cannot be gated until a customer can log
in and be recognised. That remains the blocking investment (`PROJECT.md`, and §2 of `docs/AUDIT.md`).
