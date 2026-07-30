# The post-purchase note (paste into Polar)

We do not run an email service and do not need one. Polar is merchant of record: it already sends
the receipt, the renewal and failed-payment notices, the refund confirmation, and the one-time code
that signs a customer into the portal. Duplicating those would mean two senders, two templates and
two chances to say something contradictory about money.

The one message that *is* ours — "you paid, here is how to switch it on" — is a Polar **Custom
Benefit**. Its Markdown renders in three places from a single edit:

- the checkout success page, immediately after payment
- the purchase confirmation email
- the customer portal, forever after

Configure it at **Products → tashan Pro → Benefits → + Custom**:

- **Description** (the customer-facing title): `Turn Pro on`
- **Private note**: everything below the line.

Attach it alongside the existing licence-key benefit, not instead of it — the key benefit is what
generates and delivers the key itself.

Keep this file in sync when the commands change. It is the only copy we control that a customer
reads at the exact moment they are deciding whether this was worth $6.

---

**Two commands and you're done.**

```
npx tashan-cli activate <your licence key>
npx tashan-cli doctor
```

Your licence key is on this page, in this email, and always in [your account](https://polar.sh/tashan/portal).

`activate` registers this machine and stores the key in `~/.config/tashan/key` — once per machine,
not once per shell, and nothing to add to your shell profile. Every `doctor` run then prints
**Pro · licence active**, so you can always see it is on.

**On another machine** run `activate` again with the same key. Each one registers under its own
hostname, so your account lists exactly what is active and lets you release any of them. On a
machine you are finished with, `npx tashan-cli activate --forget` hands the slot back.

**What you just bought.** Free `doctor` tells you what in your agent config is deprecated,
archived, abandoned or shadowing an official package — that stays free, for everyone, permanently.
Pro names the replacement: which capability to move to, how it measures, and why.

**Your account** — key, invoices, devices, payment method, cancellation — is at
[polar.sh/tashan/portal](https://polar.sh/tashan/portal). Sign in with the email you paid with; Polar
sends a one-time code, so there is no password to make. tashan.sh itself has no separate login and
looks the same whether you pay or not: Pro lives in your terminal.

Nothing about your config is ever uploaded. The CLI reads your local files and asks us only about
capability names.

Stuck? Reply to this email, or [hello@tashan.sh](mailto:hello@tashan.sh). Full refund within 7 days,
no questions — [tashan.sh/refunds.html](https://tashan.sh/refunds.html).
