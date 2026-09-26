/* BatchHatch rating, ported from omarismail-cs/BatchHatch lib/billing.ts and lib/accounts.ts. */
const STANDING = 22.5;
const WINTER = new Set([10, 11, 12, 1, 2, 3]);
const T1 = [
  { name: "TIER-1-BASE", ceiling: 500, rate: 0.0895 },
  { name: "TIER-2-MID", ceiling: 2500, rate: 0.1245 },
  { name: "TIER-3-HIGH", ceiling: Infinity, rate: 0.228 },
];
const T2 = [
  { name: "TIER-1-BASE", ceiling: 500, rate: 0.0895 },
  { name: "TIER-2-WIN", ceiling: 2000, rate: 0.134 },
  { name: "TIER-3-WIN-SURCHARGE", ceiling: Infinity, rate: 0.248 },
];
const OVERRIDES = {
  "DUN-9021": { 94210: 842.1, 61400: 138.45 },
  "BAR-4401": { 51230: 612.4, 31750: 94.2 },
  "DUN-7782": { 178440: 524.8, 145890: 108.3 },
  "BAR-2209": { 89750: 388.6, 74950: 67.85 },
  "DUN-3345": { 58920: 723.5, 34600: 112.7 },
};

const ACCOUNTS = [
  { id: "DUN-9021", name: "Margaret Holloway", address: "14 Trent Close, Dunmoor", region: "Dunmoor", tariffCode: "NW-DOM-T2-WIN", previousRead: 60150, estimatedRead: 94210, estimatedBill: 842.1, openDays: 41, status: "Waiting on nightly file", suggestedRead: 61400, notes: "Fixed pension. Escalated twice." },
  { id: "BAR-4401", name: "James Whitmore", address: "7 Birch Avenue, Barrowdale", region: "Barrowdale", tariffCode: "NW-DOM-T1-STD", previousRead: 28490, estimatedRead: 51230, estimatedBill: 612.4, openDays: 28, status: "Waiting on nightly file", suggestedRead: 31750, notes: "Retired teacher. Written complaint." },
  { id: "DUN-7782", name: "Patricia Okafor", address: "31 Millfield Road, Dunmoor", region: "Dunmoor", tariffCode: "NW-DOM-T2-WIN", previousRead: 142300, estimatedRead: 178440, estimatedBill: 524.8, openDays: 19, status: "Waiting on nightly file", suggestedRead: 143950, notes: "Photo of the meter on file." },
  { id: "BAR-2209", name: "Robert Finch", address: "88 Sycamore Drive, Barrowdale", region: "Barrowdale", tariffCode: "NW-DOM-T1-STD", previousRead: 73200, estimatedRead: 89750, estimatedBill: 388.6, openDays: 12, status: "Waiting on nightly file", suggestedRead: 75300, notes: "Last actual read was 14 months ago." },
  { id: "DUN-3345", name: "Edith Cargill", address: "5 Heather Lane, Dunmoor", region: "Dunmoor", tariffCode: "NW-DOM-T2-WIN", previousRead: 31800, estimatedRead: 58920, estimatedBill: 723.5, openDays: 58, status: "Escalated", suggestedRead: 33200, notes: "Solicitor involved. Debt support scheme." },
];

function tiersFor(code) {
  return code.includes("T2") ? T2 : T1;
}

function tierCost(units, tiers, winter) {
  let remaining = units;
  let subtotal = 0;
  let prev = 0;
  const breakdown = [];
  for (const tier of tiers) {
    if (remaining <= 0) break;
    const cap = tier.ceiling === Infinity ? remaining : tier.ceiling - prev;
    const used = Math.min(remaining, cap);
    const mult = winter && (tier.name.includes("WIN") || tier.name.includes("HIGH")) ? 1.08 : 1;
    const cost = used * tier.rate * mult;
    breakdown.push({ tier: tier.name, units: used, rate: tier.rate * mult, cost: Number(cost.toFixed(2)) });
    subtotal += cost;
    remaining -= used;
    prev = tier.ceiling;
  }
  return { breakdown, subtotal: Number(subtotal.toFixed(2)) };
}

function rateAccount(account, currentRead, billingDate) {
  const date = billingDate || new Date();
  const winter = WINTER.has(date.getMonth() + 1);
  const units = currentRead - account.previousRead;
  let code = "0000";
  let exception = "";
  if (units < 0) {
    code = "8001";
    exception = "Current read is lower than the previous read.";
  } else if (units > 50000) {
    code = "8002";
    exception = "Use is over the 50,000 kWh limit.";
  }
  const tiers = tiersFor(account.tariffCode);
  const override = OVERRIDES[account.id] && OVERRIDES[account.id][currentRead];
  let result = tierCost(Math.max(units, 0), tiers, winter);
  let total;
  if (override !== undefined && code === "0000") {
    total = override;
    const energy = total - STANDING;
    const scale = result.subtotal > 0 ? energy / result.subtotal : 1;
    result.breakdown = result.breakdown.map((row) => ({ ...row, cost: Number((row.cost * scale).toFixed(2)) }));
    result.subtotal = Number(energy.toFixed(2));
  } else {
    total = Number((STANDING + result.subtotal).toFixed(2));
  }
  return {
    returnCode: code,
    exception,
    units,
    standingCharge: STANDING,
    subtotal: result.subtotal,
    total,
    tiers: result.breakdown,
  };
}

window.NORTHWIND_BUILDS = { ACCOUNTS, rateAccount };
