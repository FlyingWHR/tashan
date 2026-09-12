// One USDC transfer to a known x402 receiver is one settled agent call.
//
// The manifest filters by topic2 (the Transfer event's indexed `to`), so this handler only ever
// sees transfers that landed on an address the Bazaar publishes as a payTo. That filter is what
// makes indexing the whole economy cheap: without it a subgraph on USDC/Base processes every
// transfer on the chain to find the handful that are agent payments.

import { BigInt, Bytes, store } from "@graphprotocol/graph-ts";
import { Transfer } from "../generated/USDC/USDC";
import { Receiver, Payment, ReceiverDay, Economy, Payer, PayerReceiver } from "../generated/schema";

const DAY = 86400;
const ONE = BigInt.fromI32(1);
const ZERO = BigInt.zero();

function economy(): Economy {
  let e = Economy.load("x402");
  if (e == null) {
    e = new Economy("x402");
    e.totalPaid = ZERO;
    e.payments = ZERO;
    e.receiversPaid = ZERO;
    e.lastBlock = ZERO;
  }
  return e as Economy;
}

export function handleTransfer(event: Transfer): void {
  // A zero-value transfer is a probe or an approval dance, not a payment. Counting it would let
  // anyone inflate a receiver's call count for the price of gas.
  if (event.params.value.equals(ZERO)) return;

  const to = event.params.to.toHexString();
  const from = event.params.from.toHexString();
  const ts = event.block.timestamp;
  const eco = economy();

  let r = Receiver.load(to);
  if (r == null) {
    r = new Receiver(to);
    r.totalPaid = ZERO;
    r.payments = ZERO;
    r.payers = ZERO;
    r.firstPaymentAt = ts;
    r.firstBlock = event.block.number;
    eco.receiversPaid = eco.receiversPaid.plus(ONE);
  }
  r.totalPaid = r.totalPaid.plus(event.params.value);
  r.payments = r.payments.plus(ONE);
  r.lastPaymentAt = ts;
  r.lastBlock = event.block.number;

  // Distinct payers, counted without loading an array: the pair either exists or it does not.
  const pairId = from + "-" + to;
  if (PayerReceiver.load(pairId) == null) {
    const pair = new PayerReceiver(pairId);
    pair.save();
    r.payers = r.payers.plus(ONE);
  }
  r.save();

  let p = Payer.load(from);
  if (p == null) {
    p = new Payer(from);
    p.totalPaid = ZERO;
    p.payments = ZERO;
    p.receiversPaid = ZERO;
    p.firstPaymentAt = ts;
  }
  p.totalPaid = p.totalPaid.plus(event.params.value);
  p.payments = p.payments.plus(ONE);
  p.lastPaymentAt = ts;
  p.save();

  const day = ts.toI32() / DAY;
  const dayId = to + "-" + day.toString();
  let d = ReceiverDay.load(dayId);
  if (d == null) {
    d = new ReceiverDay(dayId);
    d.receiver = to;
    d.day = day;
    d.totalPaid = ZERO;
    d.payments = ZERO;
  }
  d.totalPaid = d.totalPaid.plus(event.params.value);
  d.payments = d.payments.plus(ONE);
  d.save();

  const pay = new Payment(event.transaction.hash.toHexString() + "-" + event.logIndex.toString());
  pay.receiver = to;
  pay.payer = event.params.from;
  pay.amount = event.params.value;
  pay.block = event.block.number;
  pay.timestamp = ts;
  pay.tx = event.transaction.hash;
  pay.save();

  eco.totalPaid = eco.totalPaid.plus(event.params.value);
  eco.payments = eco.payments.plus(ONE);
  eco.lastBlock = event.block.number;
  eco.save();
}
