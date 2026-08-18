// Get tashan listed in the x402 Bazaar — by making one real payment to ourselves.
//
//   cd tools && npm i --no-save --prefix . @coinbase/cdp-sdk @x402/fetch @x402/core @x402/evm \
//                 @x402/extensions @x402/svm
//   CDP_API_KEY_ID=… CDP_API_KEY_SECRET=… CDP_WALLET_SECRET=… node bazaar_bootstrap.mjs --address
//   CDP_API_KEY_ID=… CDP_API_KEY_SECRET=… CDP_WALLET_SECRET=… node bazaar_bootstrap.mjs --pay
//
// ALL SIX PACKAGES ARE REQUIRED. @coinbase/cdp-sdk/x402 imports @x402/extensions AND @x402/svm
// (Solana) at module load even for a Base-only buyer, and neither is a declared dependency — the
// import fails at run time, not install time. Installing the four the docs name gets you two
// consecutive 'Cannot find package' errors.
//
// Install them in ONE command. `npm i --no-save` with no package.json REWRITES the tree to just
// what you asked for, so a second install silently deletes the first one's packages.
//
// `--prefix .` IS LOAD-BEARING. tashan has no package.json anywhere, so npm walks UP looking for
// one and installs into the first ancestor that has it — which here is $HOME, quietly adding 99
// packages to a directory that has nothing to do with this project. It did exactly that once.
//
// WHY THIS EXISTS. The Bazaar is the only discovery index for x402 services — 15,089 resources and
// 41,671 agents that demonstrably pay for things — and Coinbase's own seller documentation is
// explicit that there is NO registration form and NO submission API. You are indexed by completing
// a successful paid call through the CDP Facilitator. Every one of those 15,089 listings has at
// least one settled call and not one is missing its quality block. A listing is earned, not asked
// for, so the only way in is to be paid once.
//
// THE SECOND REASON, which is the better one. Our payment rail has never completed a settlement.
// check_payments.py proves VERIFICATION works — the facilitator is reachable, our CDP credential is
// accepted, the request shape is judged on payment-side grounds — but /settle only runs after a
// genuinely valid signature, and no valid signature has ever been presented. So we do not actually
// know that we can take money. This script is that test, and the Bazaar listing is its by-product.
// If settlement is broken, this is how we find out for $0.01 instead of on our first real customer.
//
// NO PRIVATE KEY IS HANDLED ANYWHERE. CdpX402Client signs inside the CDP SDK using the same API
// credentials the Worker already holds; the wallet is CDP-managed and the secret never appears
// here, in the repo, or in a log.
//
// It is deliberately NOT part of the pipeline and NOT a dependency of anything. tashan has no
// package.json on purpose — install these packages in this directory only, run it once, and
// they can be deleted. tools/node_modules is gitignored.
//
// HONESTY, because the quality block is public: this buys a LISTING, not a reputation. The Bazaar
// publishes l30DaysUniquePayers per resource, so one self-payment shows up as exactly what it is —
// one payer. Do not repeat it to make the number look better. Getting indexed is a door; walking
// through it is real demand's job, and the funnel now records that separately.

const BASE = process.env.TASHAN_BASE || "https://tashan.sh";

// One call per priced resource: the Bazaar indexes RESOURCES, not sellers, so each endpoint needs
// its own settle. Cheapest first — if the rail is broken, it breaks on the $0.01 one.
const TARGETS = [
  { url: `${BASE}/api/history?id=pkg:tavily-mcp`, method: "GET", usd: 0.01, body: null },
  { url: `${BASE}/v0.1/audit`, method: "POST", usd: 0.01,
    body: { servers: ["tavily-mcp"], history: true } },
  { url: `${BASE}/v0.1/kit`, method: "POST", usd: 0.05,
    body: { task: "web-scraping", kit: true } },
];

// OUR OWN BOOTSTRAP MUST NOT COUNT AS AGENT DEMAND. functions/api/_demand.js drops this exact
// user-agent, for the same reason /api/buy does: a metric we can inflate by testing manufactures
// the number a founder most wants to see. That already happened once here — 43 checkouts nobody
// made. Indexing is driven by the facilitator's settle, not by our analytics, so excluding
// ourselves costs the listing nothing.
const UA = "tashan-payment-check/bazaar-bootstrap";

function bail(msg, code = 1) {
  console.error(`\n  ${msg}\n`);
  process.exit(code);
}

async function client() {
  let CdpX402Client, wrapFetchWithPayment;
  try {
    ({ CdpX402Client } = await import("@coinbase/cdp-sdk/x402"));
    ({ wrapFetchWithPayment } = await import("@x402/fetch"));
  } catch (e) {
    bail("Dependencies are not installed. In this directory run:\n" +
         "    npm i --no-save --prefix . @coinbase/cdp-sdk @x402/fetch @x402/core @x402/evm \\\n" +
         "      @x402/extensions @x402/svm\n" +
         `  (${e.message})`);
  }
  for (const k of ["CDP_API_KEY_ID", "CDP_API_KEY_SECRET", "CDP_WALLET_SECRET"]) {
    if (!process.env[k]) {
      bail(`${k} is not set.\n` +
           "  API key id/secret: the same pair in the Pages secrets (X402_CDP_KEY_ID /\n" +
           "  X402_CDP_KEY_SECRET). Wallet secret: portal.cdp.coinbase.com -> Server Wallets.\n" +
           "  Never paste any of them into a chat.");
    }
  }
  // No argument = Base mainnet. Passing "development" would target Base Sepolia, where a settle
  // proves the code path but earns nothing on the mainnet index we are trying to enter.
  return { cdp: new CdpX402Client(), wrap: wrapFetchWithPayment };
}

async function main() {
  const showAddress = process.argv.includes("--address");
  const pay = process.argv.includes("--pay");
  if (!showAddress && !pay) bail("Pass --address (see where to send USDC) or --pay (settle).", 2);

  const { cdp, wrap } = await client();
  const { evmAddress } = await cdp.getAddresses();

  if (showAddress) {
    console.log(`\n  CDP-managed buyer wallet:  ${evmAddress}`);
    console.log("  Network:                   Base mainnet (eip155:8453)");
    console.log("  Send:                      ~$1 of USDC on BASE (contract");
    console.log("                             0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913)");
    console.log("  Spent by --pay:            $0.07 total. The rest stays yours and is withdrawable.");
    console.log("  No ETH needed:             the facilitator submits the transaction and pays gas.\n");
    console.log("  NOT the same address as the RECEIVING wallet (X402_PAY_TO). That one still needs");
    console.log("  no funding — it only ever receives.\n");
    return 0;
  }

  const fetchPaid = wrap(globalThis.fetch, cdp);
  let ok = 0;
  for (const t of TARGETS) {
    process.stdout.write(`  ${t.method} ${t.url.replace(BASE, "")} ($${t.usd.toFixed(2)}) ... `);
    try {
      const r = await fetchPaid(t.url, {
        method: t.method,
        headers: { "user-agent": UA, ...(t.body ? { "content-type": "application/json" } : {}) },
        ...(t.body ? { body: JSON.stringify(t.body) } : {}),
      });
      // The receipt is the whole point: a 200 with no PAYMENT-RESPONSE means we served the content
      // without being paid, which is a worse outcome than a refusal and must not read as success.
      const receipt = r.headers.get("payment-response") || r.headers.get("x-payment-response");
      if (r.ok && receipt) { console.log(`SETTLED (${r.status})`); ok++; }
      else if (r.ok) console.log(`200 but NO settlement receipt — served unpaid, investigate`);
      else console.log(`FAILED ${r.status} — ${(await r.text()).slice(0, 180)}`);
    } catch (e) {
      console.log(`ERROR — ${e.message}`);
    }
  }
  console.log(`\n  ${ok}/${TARGETS.length} settled.`);
  if (ok) {
    console.log("  Indexing is not instant. Confirm with:  python3 pipeline/bazaar.py");
    console.log("  It prints TASHAN: LISTED once the resources appear.\n");
  }
  return ok === TARGETS.length ? 0 : 1;
}

main().then((c) => process.exit(c)).catch((e) => bail(e.stack || String(e)));
