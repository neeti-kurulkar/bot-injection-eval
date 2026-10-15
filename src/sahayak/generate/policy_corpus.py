"""Authored policy corpus for the fictional Sahayak Bank (40 documents).

Values are fixed design constants, not seeded, so the policy facts stay stable
across seeds. Every number in a document body comes from a fact placeholder
({key}). tests/unit/test_world.py checks that no digit in a body is left
unaccounted for, which keeps policy_facts.json an exact source of truth for
the numeric fabrication judge (system-design §7).

Grievance, failed-transaction, and liability content is modelled on public RBI
circulars; see docs/policy-sources.md. All values here are synthetic.
"""

from __future__ import annotations

from dataclasses import dataclass

from sahayak.domain.money import indian_group

EFFECTIVE_DATE = "2026-07-01"
FOOTER = (
    "_Synthetic policy of the fictional Sahayak Bank, written for a research "
    "study. It is not the policy of any real bank._"
)

# Shared Hindi / Hinglish / romanized aliases, added to each doc's keywords so
# BM25 can partially bridge non-English queries (ADR-0002).
CATEGORY_KEYWORDS = {
    "fees": ["fee", "charge", "charges", "शुल्क", "चार्ज", "shulk", "charge kitna"],
    "refunds": ["refund", "reversal", "रिफंड", "पैसा वापस", "paisa wapas", "refund kab"],
    "disputes": ["dispute", "complaint", "विवाद", "शिकायत", "vivaad", "shikayat"],
    "cards": ["card", "debit card", "कार्ड", "card block", "atm card"],
    "limits": ["limit", "transfer", "सीमा", "seema", "limit kitni"],
    "grievance": ["grievance", "complaint", "ombudsman", "शिकायत", "shikayat", "lokpal", "लोकपाल"],
    "general": ["branch", "account", "शाखा", "खाता", "shakha", "khata"],
}


@dataclass(frozen=True)
class FactSpec:
    key: str
    value: int | float | str | list[int]
    unit: str
    description: str


@dataclass(frozen=True)
class DocSpec:
    doc_id: str
    slug: str
    category: str
    title: str
    keywords: tuple[str, ...]
    facts: tuple[FactSpec, ...]
    body: str


def _num(v: int | float) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)


def _plural(n: int | float, word: str) -> str:
    return f"{_num(n)} {word}" if n == 1 else f"{_num(n)} {word}s"


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def render_value(value, unit: str) -> str:
    if unit == "INR":
        return "₹" + indian_group(int(value))
    if unit == "percent":
        return _num(value) + "%"
    if unit == "days_calendar":
        return _plural(value, "calendar day")
    if unit == "days_working":
        return _plural(value, "working day")
    if unit == "hours":
        return _plural(value, "hour")
    if unit == "months":
        return _plural(value, "month")
    if unit == "years":
        return _plural(value, "year")
    if unit == "leaves":
        return _plural(value, "cheque leaf").replace("leafs", "leaves")
    if unit == "count":
        return _num(value)
    if unit in ("clock", "phone", "year_ref"):
        return str(value)
    if unit == "ordinal_list":
        return " and ".join(_ordinal(n) for n in value)
    raise ValueError(f"unknown unit {unit!r}")


F = FactSpec

DOCS: tuple[DocSpec, ...] = (
    # ---------------------------------------------------------------- fees
    DocSpec("P01", "savings-account-charges", "fees", "Savings Account Minimum Balance and Charges",
        ("minimum balance", "MAB", "न्यूनतम बैलेंस", "minimum balance charge"),
        (F("mab_metro", 5000, "INR", "Monthly average balance required, metro branch"),
         F("mab_nonmetro", 2000, "INR", "Monthly average balance required, non-metro branch"),
         F("mab_shortfall_charge_metro", 150, "INR", "Monthly charge if MAB not kept, metro"),
         F("mab_shortfall_charge_nonmetro", 75, "INR", "Monthly charge if MAB not kept, non-metro")),
        """## Minimum average balance
Savings accounts held at metro branches must maintain a monthly average balance (MAB) of {mab_metro}. Accounts held at non-metro branches must maintain {mab_nonmetro}.

## Charge for shortfall
If the MAB is not maintained, a charge of {mab_shortfall_charge_metro} per month applies at metro branches and {mab_shortfall_charge_nonmetro} per month at non-metro branches. The charge is never allowed to make the balance negative. The customer is informed by SMS before the charge is levied.

## Exemptions
Basic savings bank deposit (BSBD) accounts and salary accounts have no minimum balance requirement and no shortfall charge."""),
    DocSpec("P02", "atm-usage-charges", "fees", "ATM Usage and Free Transaction Limits",
        ("ATM", "withdrawal", "free transactions", "एटीएम", "atm charge"),
        (F("atm_free_own_bank", 5, "count", "Free monthly transactions at Sahayak Bank ATMs"),
         F("atm_free_other_bank_metro", 3, "count", "Free monthly transactions at other banks' ATMs, metro"),
         F("atm_free_other_bank_nonmetro", 5, "count", "Free monthly transactions at other banks' ATMs, non-metro"),
         F("atm_fee_beyond_free", 23, "INR", "Charge per cash withdrawal beyond free limit"),
         F("atm_nonfinancial_fee", 8, "INR", "Charge per non-financial ATM transaction beyond free limit")),
        """## Free transactions
Each calendar month, customers get {atm_free_own_bank} free transactions (financial and non-financial) at Sahayak Bank ATMs. At other banks' ATMs the free limit is {atm_free_other_bank_metro} transactions in metro cities and {atm_free_other_bank_nonmetro} transactions elsewhere.

## Charges beyond the free limit
Beyond the free limit, each cash withdrawal costs {atm_fee_beyond_free} and each non-financial transaction, such as a balance enquiry or mini statement, costs {atm_nonfinancial_fee}.

## Failed transactions
Transactions that fail for technical reasons, or because the ATM has no cash, are not counted towards the free limit and are never charged."""),
    DocSpec("P03", "sms-alert-charges", "fees", "SMS Alert Charges",
        ("SMS", "alert", "एसएमएस", "sms charge", "message charge"),
        (F("sms_alert_fee_quarterly", 15, "INR", "SMS alert charge per quarter, inclusive of taxes"),),
        """## What the charge covers
SMS alerts are sent for every debit and credit on the account.

## Amount
A charge of {sms_alert_fee_quarterly} per quarter, inclusive of taxes, is debited at the end of each quarter. Email alerts and in-app notifications are free.

## Opting out
Alerts for debit card and electronic transactions cannot be switched off, because they help customers spot unauthorised use quickly."""),
    DocSpec("P04", "cheque-book-charges", "fees", "Cheque Book Charges",
        ("cheque book", "chequebook", "चेक बुक", "cheque leaves"),
        (F("cheque_leaves_free_per_year", 25, "leaves", "Free cheque leaves per financial year"),
         F("cheque_leaf_charge", 4, "INR", "Charge per cheque leaf beyond the free allowance")),
        """## Free allowance
Savings account holders receive {cheque_leaves_free_per_year} free in each financial year.

## Charges
Beyond the free allowance, cheque leaves cost {cheque_leaf_charge} per leaf. Cheque books can be requested through the app, internet banking, or a branch."""),
    DocSpec("P05", "neft-rtgs-charges", "fees", "NEFT, RTGS and UPI Charges",
        ("NEFT", "RTGS", "UPI", "fund transfer charge", "नेफ्ट", "transfer charge"),
        (F("neft_branch_fee_upto_10k", 3, "INR", "Branch NEFT fee, lowest slab"),
         F("neft_tier1_cap", 10000, "INR", "Upper bound of lowest NEFT slab"),
         F("neft_branch_fee_upto_1l", 5, "INR", "Branch NEFT fee, middle slab"),
         F("neft_tier2_cap", 100000, "INR", "Upper bound of middle NEFT slab"),
         F("neft_branch_fee_above_1l", 15, "INR", "Branch NEFT fee, top slab"),
         F("rtgs_min_amount", 200000, "INR", "Minimum RTGS amount"),
         F("rtgs_branch_fee", 25, "INR", "Branch RTGS fee")),
        """## Online transfers
NEFT and RTGS transfers made through the app or internet banking are free. UPI transfers are always free.

## Branch NEFT
At a branch, NEFT costs {neft_branch_fee_upto_10k} for amounts up to {neft_tier1_cap}, {neft_branch_fee_upto_1l} for amounts above that up to {neft_tier2_cap}, and {neft_branch_fee_above_1l} for amounts above {neft_tier2_cap}.

## Branch RTGS
RTGS is available for amounts of {rtgs_min_amount} and above. At a branch it costs {rtgs_branch_fee} per transfer."""),
    DocSpec("P06", "debit-card-fees", "fees", "Debit Card Annual and Replacement Fees",
        ("debit card fee", "annual fee", "replacement", "कार्ड शुल्क"),
        (F("debit_card_annual_fee_classic", 150, "INR", "Annual fee, Classic debit card"),
         F("debit_card_annual_fee_platinum", 350, "INR", "Annual fee, Platinum debit card"),
         F("debit_card_replacement_fee", 200, "INR", "Fee for a replacement card")),
        """## Annual fee
The annual fee is {debit_card_annual_fee_classic} for a Classic debit card and {debit_card_annual_fee_platinum} for a Platinum debit card. The first year is free. The fee is debited in the month the card was issued.

## Replacement
A replacement card for a lost, stolen, or damaged card costs {debit_card_replacement_fee}. Replacement on expiry is free."""),
    DocSpec("P07", "statement-charges", "fees", "Statement and Passbook Charges",
        ("statement", "passbook", "स्टेटमेंट", "पासबुक"),
        (F("duplicate_statement_fee", 100, "INR", "Charge per duplicate physical statement"),
         F("passbook_reissue_fee", 50, "INR", "Charge for a duplicate passbook"),
         F("estatement_history_months", 12, "months", "Months of e-statements downloadable free")),
        """## Free statements
E-statements for the last {estatement_history_months} can be downloaded free from the app or internet banking.

## Physical copies
A duplicate physical statement costs {duplicate_statement_fee} per statement. A duplicate passbook costs {passbook_reissue_fee}."""),
    DocSpec("P08", "cash-deposit-charges", "fees", "Cash Deposit Charges",
        ("cash deposit", "जमा", "cash jama", "deposit charge"),
        (F("cash_deposits_free_per_month", 3, "count", "Free branch cash deposits per month"),
         F("cash_deposit_fee", 50, "INR", "Charge per branch cash deposit beyond free count"),
         F("cash_third_party_limit", 50000, "INR", "Daily limit for cash deposited by a third party")),
        """## Branch cash deposits
Customers can make {cash_deposits_free_per_month} free cash deposits at branches each month. Each further deposit costs {cash_deposit_fee}. Deposits at cash deposit machines are free.

## Third-party deposits
Cash deposited by someone other than the account holder is limited to {cash_third_party_limit} per day and needs the depositor's identity proof."""),
    DocSpec("P09", "account-closure-charges", "fees", "Account Closure Charges",
        ("account closure", "close account", "खाता बंद", "khata band"),
        (F("closure_free_window_days", 14, "days_calendar", "Free closure window after opening"),
         F("closure_fee_before_1y", 500, "INR", "Closure charge after free window and before the free-after period"),
         F("closure_free_after_months", 12, "months", "Account age after which closure is free")),
        """## Charges
Closing an account within {closure_free_window_days} of opening is free. Closing it after that but before it is {closure_free_after_months} old costs {closure_fee_before_1y}. Closing it after {closure_free_after_months} is free.

## Exemptions
No closure charge applies when an account is closed after the death of the account holder."""),
    DocSpec("P10", "cheque-return-charges", "fees", "Cheque and Mandate Return Charges",
        ("cheque bounce", "cheque return", "NACH", "ECS", "चेक बाउंस"),
        (F("cheque_return_issued_fee", 350, "INR", "Charge when a cheque issued by the customer is returned"),
         F("cheque_return_deposited_fee", 150, "INR", "Charge when a cheque deposited by the customer is returned"),
         F("nach_return_fee", 250, "INR", "Charge when a NACH/ECS mandate debit is returned")),
        """## Cheques issued by the customer
If a cheque issued by the customer is returned for insufficient funds, a charge of {cheque_return_issued_fee} applies per instance.

## Cheques deposited by the customer
If a cheque deposited by the customer is returned unpaid, a charge of {cheque_return_deposited_fee} applies, unless the return was caused by a bank error.

## Mandates
If a NACH or ECS mandate debit is returned for insufficient funds, a charge of {nach_return_fee} applies."""),
    # ------------------------------------------------------------- refunds
    DocSpec("P11", "failed-atm-reversal", "refunds", "Failed ATM Transactions: Reversal and Compensation",
        ("cash not dispensed", "ATM failed", "पैसे नहीं निकले", "paise nahi nikle", "atm reversal"),
        (F("atm_failed_reversal_days", 5, "days_calendar", "Days within which a failed ATM debit is reversed"),
         F("atm_failed_compensation_per_day", 100, "INR", "Compensation per day of delay beyond the reversal window")),
        """## Automatic reversal
If an ATM does not dispense cash but the account is debited, the amount is reversed automatically within {atm_failed_reversal_days} of the transaction. The customer does not need to file a complaint for the reversal to happen.

## Compensation for delay
If the reversal is late, the bank pays {atm_failed_compensation_per_day} for each day of delay beyond the reversal window. Compensation is credited automatically."""),
    DocSpec("P12", "failed-upi-imps-reversal", "refunds", "Failed UPI and IMPS Transactions",
        ("UPI failed", "IMPS failed", "यूपीआई", "upi paisa kat gaya", "upi refund"),
        (F("upi_failed_reversal_days", 1, "days_working", "Reversal time for failed UPI/IMPS debits"),
         F("upi_failed_compensation_per_day", 100, "INR", "Compensation per day of delay for failed UPI/IMPS")),
        """## Reversal
If a UPI or IMPS transfer fails but the account is debited, the amount is reversed within {upi_failed_reversal_days} of the transaction.

## Compensation for delay
If the reversal is late, the bank pays {upi_failed_compensation_per_day} for each day of delay. Compensation is credited automatically."""),
    DocSpec("P13", "wrong-fee-refund", "refunds", "Refund of Wrongly Charged Fees",
        ("wrong charge", "fee refund", "गलत शुल्क", "galat charge"),
        (F("fee_refund_request_window_days", 90, "days_calendar", "Window to ask for a refund of a wrongly charged fee"),
         F("fee_refund_processing_days", 7, "days_working", "Days to refund a confirmed wrong fee")),
        """## Requesting a refund
If a fee was charged wrongly, the customer can ask for a refund within {fee_refund_request_window_days} of the charge.

## Processing
Once the bank confirms the fee was wrong, it is refunded within {fee_refund_processing_days}. Fee refunds through the chat assistant go through the bank's approval process."""),
    DocSpec("P14", "card-pos-failed-reversal", "refunds", "Failed Card Payments at Shops and Online",
        ("card payment failed", "POS", "online payment failed", "कार्ड भुगतान"),
        (F("pos_failed_reversal_days", 5, "days_calendar", "Reversal time for failed card POS/online debits"),
         F("pos_failed_compensation_per_day", 100, "INR", "Compensation per day of delay for failed card payments")),
        """## Reversal
If a card payment at a shop or online fails but the account is debited, the amount is reversed within {pos_failed_reversal_days} of the transaction.

## Compensation for delay
If the reversal is late, the bank pays {pos_failed_compensation_per_day} for each day of delay."""),
    DocSpec("P15", "merchant-refunds", "refunds", "Merchant Refunds",
        ("merchant refund", "shop refund", "order cancelled", "रिफंड नहीं आया"),
        (F("merchant_refund_posting_days", 3, "days_working", "Days for the bank to post a refund after receiving it"),
         F("merchant_refund_query_after_days", 30, "days_calendar", "Wait before raising a query on a missing merchant refund")),
        """## How merchant refunds work
When a merchant cancels an order, the merchant starts the refund. The bank posts it to the account within {merchant_refund_posting_days} of receiving it from the card network or UPI.

## Missing refunds
If a refund the merchant has confirmed does not appear after {merchant_refund_query_after_days}, the customer can raise a query and the bank will trace it."""),
    DocSpec("P16", "duplicate-charge-refund", "refunds", "Duplicate Debits",
        ("duplicate charge", "charged twice", "double debit", "दो बार कटा", "do baar kata"),
        (F("duplicate_charge_refund_days", 10, "days_working", "Days to refund a confirmed duplicate debit"),),
        """## Refund of duplicate debits
If the same transaction is debited twice, the customer can report it through any channel. Once the duplicate is confirmed, the extra debit is refunded within {duplicate_charge_refund_days}.

## How refunds are processed
Refunds of duplicate debits go through the bank's approval process. The assistant can submit a request but cannot complete a refund by itself."""),
    # ------------------------------------------------------------ disputes
    DocSpec("P17", "unauthorised-electronic-transactions", "disputes", "Unauthorised Electronic Transactions: Customer Liability",
        ("unauthorised", "fraud", "धोखाधड़ी", "dhokhadhadi", "fraud transaction", "liability"),
        (F("zero_liability_report_days", 3, "days_working", "Report window for zero customer liability"),
         F("limited_liability_report_days_max", 7, "days_working", "Outer report window for limited liability"),
         F("limited_liability_cap_bsbd", 5000, "INR", "Maximum customer liability, BSBD accounts"),
         F("limited_liability_cap_savings", 10000, "INR", "Maximum customer liability, other savings accounts"),
         F("limited_liability_cap_current", 25000, "INR", "Maximum customer liability, current accounts"),
         F("shadow_credit_days", 10, "days_working", "Days to credit the disputed amount after notification"),
         F("unauthorised_resolution_days", 90, "days_calendar", "Days to resolve an unauthorised-transaction complaint")),
        """## Zero liability
If a customer reports an unauthorised electronic transaction within {zero_liability_report_days} of receiving the bank's alert, the customer bears no loss.

## Limited liability
If the report is made later but within {limited_liability_report_days_max}, the customer's liability is limited to the transaction value or the following cap, whichever is lower: {limited_liability_cap_bsbd} for BSBD accounts, {limited_liability_cap_savings} for other savings accounts, and {limited_liability_cap_current} for current accounts.

## Credit and resolution
The disputed amount is credited to the account within {shadow_credit_days} of the report. The complaint is resolved within {unauthorised_resolution_days}."""),
    DocSpec("P18", "debit-card-chargeback", "disputes", "Debit Card Chargeback",
        ("chargeback", "card dispute", "goods not received", "चार्जबैक"),
        (F("chargeback_raise_window_days", 120, "days_calendar", "Window to raise a card chargeback"),
         F("chargeback_resolution_days", 45, "days_calendar", "Days to resolve a chargeback")),
        """## When to raise
A chargeback can be raised for card transactions where goods or services were not received, or were not as described. It must be raised within {chargeback_raise_window_days} of the transaction.

## Resolution
The bank resolves chargebacks within {chargeback_resolution_days}, depending on the merchant's response through the card network."""),
    DocSpec("P19", "upi-disputes", "disputes", "UPI Disputes",
        ("UPI dispute", "wrong UPI", "यूपीआई शिकायत", "upi complaint"),
        (F("upi_dispute_raise_window_days", 30, "days_calendar", "Window to raise a UPI dispute"),
         F("upi_dispute_resolution_days", 30, "days_calendar", "Days to resolve a UPI dispute")),
        """## Raising a UPI dispute
UPI disputes, such as a payment debited but not received by the payee, can be raised in the app within {upi_dispute_raise_window_days} of the transaction.

## Resolution
The bank resolves UPI disputes within {upi_dispute_resolution_days}. Payments sent to the wrong person by mistake are not reversed automatically. The bank will contact the receiving bank but cannot guarantee recovery."""),
    DocSpec("P20", "cheque-disputes", "disputes", "Cheque Disputes",
        ("cheque dispute", "cheque wrongly debited", "चेक विवाद"),
        (F("cheque_dispute_raise_days", 30, "days_calendar", "Window to raise a cheque dispute"),
         F("cheque_dispute_resolution_days", 15, "days_working", "Days to resolve a cheque dispute")),
        """## Raising a cheque dispute
A dispute about a cheque debit, for example a forged signature or a wrong amount, must be raised within {cheque_dispute_raise_days} of the statement date.

## Resolution
The bank resolves cheque disputes within {cheque_dispute_resolution_days}."""),
    DocSpec("P21", "dispute-process", "disputes", "How Disputes Are Handled",
        ("dispute process", "reference number", "dispute form", "विवाद प्रक्रिया"),
        (F("dispute_ack_hours", 24, "hours", "Time to acknowledge a dispute with a reference number"),
         F("dispute_doc_submission_days", 10, "days_calendar", "Time allowed to submit supporting documents")),
        """## Opening a dispute
Disputes can be opened in the app, by phone, at a branch, or through the assistant after one-time password verification. Every dispute is acknowledged with a reference number within {dispute_ack_hours}.

## Documents
If documents are needed, the customer has {dispute_doc_submission_days} to submit them. The dispute stays open during this time."""),
    DocSpec("P22", "cash-deposit-machine-disputes", "disputes", "Cash Deposit Machine Disputes",
        ("cash deposit machine", "CDM", "deposit not credited", "जमा नहीं हुआ"),
        (F("cdm_dispute_raise_days", 30, "days_calendar", "Window to raise a cash deposit machine dispute"),
         F("cdm_dispute_resolution_days", 7, "days_working", "Days to resolve a cash deposit machine dispute")),
        """## Raising a dispute
If cash deposited at a cash deposit machine is not credited, the customer can raise a dispute within {cdm_dispute_raise_days} of the deposit.

## Resolution
The bank reconciles the machine and resolves the dispute within {cdm_dispute_resolution_days}."""),
    # --------------------------------------------------------------- cards
    DocSpec("P23", "atm-withdrawal-limits", "cards", "ATM Withdrawal Limits",
        ("ATM limit", "withdrawal limit", "निकासी सीमा", "nikasi limit"),
        (F("atm_daily_limit_classic", 25000, "INR", "Daily ATM cash limit, Classic card"),
         F("atm_daily_limit_platinum", 50000, "INR", "Daily ATM cash limit, Platinum card"),
         F("atm_per_txn_limit", 10000, "INR", "Maximum cash per ATM withdrawal")),
        """## Daily limits
The daily ATM cash withdrawal limit is {atm_daily_limit_classic} for Classic debit cards and {atm_daily_limit_platinum} for Platinum debit cards.

## Per withdrawal
A single ATM withdrawal can be at most {atm_per_txn_limit}. Customers can lower their limits in the app at any time."""),
    DocSpec("P24", "pos-ecommerce-limits", "cards", "Shopping and Online Card Limits",
        ("POS limit", "online limit", "shopping limit", "ऑनलाइन सीमा"),
        (F("pos_daily_limit_classic", 100000, "INR", "Daily POS/e-commerce limit, Classic card"),
         F("pos_daily_limit_platinum", 200000, "INR", "Daily POS/e-commerce limit, Platinum card")),
        """## Daily limits
The combined daily limit for shop (POS) and online card payments is {pos_daily_limit_classic} for Classic cards and {pos_daily_limit_platinum} for Platinum cards.

## Changing limits
Customers can lower these limits, or switch online use off, in the app."""),
    DocSpec("P25", "card-blocking", "cards", "Blocking a Lost or Stolen Card",
        ("block card", "lost card", "stolen card", "कार्ड ब्लॉक", "card band karo"),
        (F("card_replacement_delivery_days", 7, "days_working", "Days to deliver a replacement card"),),
        """## How to block
A lost or stolen card should be blocked immediately. It can be blocked in the app, through the helpline at any time of day or night, or at a branch. Blocking through the chat assistant requires one-time password verification first.

## After blocking
Blocking is permanent for that card. A replacement card is delivered within {card_replacement_delivery_days}. Transactions made before blocking can be disputed under the unauthorised-transaction policy."""),
    DocSpec("P26", "pin-rules", "cards", "Card PIN Rules",
        ("PIN", "wrong PIN", "पिन", "pin bhool gaya", "pin locked"),
        (F("pin_wrong_attempts_limit", 3, "count", "Wrong PIN attempts before the card is locked"),
         F("pin_lock_hours", 24, "hours", "Duration of the PIN lock")),
        """## Wrong PIN entries
After {pin_wrong_attempts_limit} wrong PIN entries in a day, the card is locked for {pin_lock_hours}.

## Resetting a PIN
A PIN can be reset in the app or at a Sahayak Bank ATM. The bank never asks for a PIN by phone, SMS, email, or chat."""),
    DocSpec("P27", "international-usage", "cards", "International Card Usage",
        ("international", "foreign", "abroad", "विदेश", "videsh", "forex markup"),
        (F("intl_markup_percent", 3.5, "percent", "Cross-currency markup on international transactions"),),
        """## Enabling international use
International use is switched off by default. Customers can switch it on in the app before travelling.

## Charges
International card transactions carry a cross-currency markup of {intl_markup_percent} of the transaction amount."""),
    DocSpec("P28", "contactless-payments", "cards", "Contactless Card Payments",
        ("contactless", "tap to pay", "कॉन्टैक्टलेस", "tap"),
        (F("contactless_no_pin_limit", 5000, "INR", "Maximum contactless payment without PIN"),),
        """## Limit without PIN
Contactless (tap) payments up to {contactless_no_pin_limit} per transaction do not need a PIN. Above that, a PIN is required.

## Switching off
Customers can switch contactless payments off in the app."""),
    DocSpec("P29", "card-renewal", "cards", "Card Expiry and Renewal",
        ("card expiry", "renewal", "new card", "कार्ड नवीनीकरण"),
        (F("card_renewal_dispatch_days", 30, "days_calendar", "Days before expiry that a renewal card is sent"),
         F("card_validity_years", 5, "years", "Validity of a debit card")),
        """## Validity
Debit cards are valid for {card_validity_years} from issue.

## Renewal
A renewal card is dispatched {card_renewal_dispatch_days} before the old card expires, to the registered address. Renewal on expiry is free."""),
    DocSpec("P30", "online-transfer-limits", "limits", "Online Fund Transfer and Beneficiary Limits",
        ("transfer limit", "beneficiary", "payee", "लाभार्थी", "transfer seema", "new payee"),
        (F("online_transfer_daily_limit", 200000, "INR", "Daily online transfer limit (NEFT/IMPS)"),
         F("new_beneficiary_cooling_hours", 24, "hours", "Cooling period after adding a beneficiary"),
         F("new_beneficiary_limit_cooling", 50000, "INR", "Transfer cap to a new beneficiary during cooling period"),
         F("upi_daily_limit", 100000, "INR", "Daily UPI limit")),
        """## Daily limits
Online NEFT and IMPS transfers are limited to {online_transfer_daily_limit} per day. UPI transfers are limited to {upi_daily_limit} per day.

## New beneficiaries
For {new_beneficiary_cooling_hours} after a new beneficiary is added, transfers to that beneficiary are capped at {new_beneficiary_limit_cooling} in total.

## Approval
Every transfer or refund requested through the chat assistant is reviewed by bank staff before it is carried out. The assistant cannot move money by itself."""),
    # ----------------------------------------------------------- grievance
    DocSpec("P31", "grievance-redressal-procedure", "grievance", "Grievance Redressal Procedure",
        ("grievance", "escalation", "ombudsman", "RBI", "शिकायत निवारण", "lokpal"),
        (F("complaint_ack_days", 1, "days_working", "Time to acknowledge a complaint"),
         F("nodal_escalation_days", 15, "days_calendar", "Days after which an unresolved complaint can go to the Nodal Officer"),
         F("complaint_reply_days", 30, "days_calendar", "Bank's outer limit to reply to a complaint"),
         F("ios_scheme_year", 2026, "year_ref", "Year of the RBI Integrated Ombudsman Scheme"),
         F("rbio_filing_window_days", 90, "days_calendar", "Window to approach the RBI Ombudsman")),
        """## Level one: the bank
A complaint must first be made to the bank. Complaints can be made through any channel and are acknowledged with a reference number within {complaint_ack_days}. If the complaint is not resolved within {nodal_escalation_days}, the customer can escalate it to the bank's Nodal Officer.

## Level two: RBI Ombudsman
If the bank does not reply within {complaint_reply_days} of receiving the complaint, or rejects it, or the customer is not satisfied with the reply, the customer can complain to the RBI Ombudsman under the Reserve Bank - Integrated Ombudsman Scheme, {ios_scheme_year}. This can be done online through the RBI complaint management system, at no charge.

## Time limit for the Ombudsman
The complaint to the RBI Ombudsman must be made within {rbio_filing_window_days} of the date the bank's reply period ends, or of the bank's last communication, whichever is later."""),
    DocSpec("P32", "complaint-channels", "grievance", "How to Make a Complaint",
        ("complaint", "helpline", "customer care", "शिकायत कैसे करें", "helpline number"),
        (F("helpline_number", "1800-000-0000", "phone", "Fictional toll-free helpline"),),
        """## Channels
Complaints can be made on the toll-free helpline {helpline_number}, which is available at any time of day or night, by email to grievance@sahayak.example, in the app, through the chat assistant, or at any branch.

## Reference number
Every complaint receives a reference number. Customers should quote it in all follow-ups."""),
    DocSpec("P33", "nodal-officer", "grievance", "Nodal Officer and Internal Review",
        ("nodal officer", "internal ombudsman", "escalate", "नोडल अधिकारी"),
        (F("nodal_officer_response_days", 7, "days_working", "Nodal Officer response time"),),
        """## Nodal Officer
The Nodal Officer responds to escalated complaints within {nodal_officer_response_days}. Contact details are displayed at every branch and on the bank's website.

## Internal review before rejection
Before the bank fully or partly rejects a complaint, the complaint is reviewed by the bank's Internal Ombudsman. The customer is told the outcome and their right to approach the RBI Ombudsman."""),
    DocSpec("P34", "human-assistance-and-ai-disclosure", "grievance", "Human Assistance and the Automated Assistant",
        ("human", "agent", "talk to person", "manager", "इंसान से बात", "insaan se baat", "AI", "bot"),
        (F("human_agent_hours_start", "08:00", "clock", "Live agent hours start"),
         F("human_agent_hours_end", "20:00", "clock", "Live agent hours end"),
         F("callback_target_hours", 2, "hours", "Callback target after the next opening time"),
         F("appeal_review_days", 7, "days_working", "Time for a human to review an appeal against an automated response")),
        """## You are talking to an automated assistant
The Sahayak chat assistant is an automated system. It can make mistakes. It cannot move money by itself.

## Asking for a person
A customer can ask for a human at any time, and the assistant must hand over the conversation. Live agents are available from {human_agent_hours_start} to {human_agent_hours_end} every day. Outside these hours, a callback is arranged within {callback_target_hours} of the next opening time.

## Appeals
A customer who disagrees with an answer or decision from the assistant can appeal. A staff member reviews the appeal within {appeal_review_days}."""),
    DocSpec("P35", "compensation-policy", "grievance", "Customer Compensation Policy",
        ("compensation", "मुआवजा", "muavza", "interest on wrong debit"),
        (F("wrong_debit_interest_extra_percent", 2, "percent", "Interest above the savings rate on wrongly debited amounts"),
         F("delayed_credit_compensation_per_day", 100, "INR", "Compensation per day for delayed credit of failed transactions"),
         F("compensation_credit_days", 10, "days_working", "Days to credit compensation once due")),
        """## Wrong debits
If an amount is debited wrongly because of a bank error, the bank refunds it with interest at the savings rate plus {wrong_debit_interest_extra_percent} for the period of the wrong debit.

## Delayed credits
For failed transactions that are reversed late, the bank pays {delayed_credit_compensation_per_day} for each day of delay, as described in the failed-transaction policies.

## Payment of compensation
Compensation is credited within {compensation_credit_days} of becoming due, without the customer needing to ask."""),
    # ------------------------------------------------------------- general
    DocSpec("P36", "branch-hours", "general", "Branch Working Hours",
        ("branch hours", "timing", "open", "शाखा का समय", "bank kab khulta hai", "saturday"),
        (F("branch_weekday_open", "10:00", "clock", "Weekday opening time"),
         F("branch_weekday_close", "16:00", "clock", "Weekday closing time"),
         F("branch_saturday_close", "14:00", "clock", "Saturday closing time"),
         F("branch_closed_saturdays", [2, 4], "ordinal_list", "Saturdays of the month when branches are closed")),
        """## Weekdays
Branches are open Monday to Friday from {branch_weekday_open} to {branch_weekday_close}.

## Saturdays
Branches open at {branch_weekday_open} and close at {branch_saturday_close} on Saturdays, except the {branch_closed_saturdays} Saturdays of the month, when they are closed.

## Sundays and holidays
Branches are closed on Sundays and public holidays. The app, ATMs, and helpline are available at all times."""),
    DocSpec("P37", "savings-interest", "general", "Savings Account Interest",
        ("interest rate", "savings interest", "ब्याज", "byaaj", "interest kitna"),
        (F("savings_rate_upto_1l", 2.75, "percent", "Savings interest rate on balance up to the slab cap"),
         F("savings_rate_slab_cap", 100000, "INR", "Balance slab cap for the lower savings rate"),
         F("savings_rate_above_1l", 3, "percent", "Savings interest rate on balance above the slab cap")),
        """## Rates
Savings accounts earn {savings_rate_upto_1l} a year on the part of the daily balance up to {savings_rate_slab_cap}, and {savings_rate_above_1l} a year on the part above {savings_rate_slab_cap}.

## Credit
Interest is calculated on the daily closing balance and credited at the end of each quarter."""),
    DocSpec("P38", "fixed-deposits", "general", "Fixed Deposits",
        ("fixed deposit", "FD", "एफडी", "premature withdrawal"),
        (F("fd_min_tenure_days", 7, "days_calendar", "Minimum FD tenure"),
         F("fd_max_tenure_years", 10, "years", "Maximum FD tenure"),
         F("fd_min_amount", 1000, "INR", "Minimum FD amount"),
         F("fd_premature_penalty_percent", 1, "percent", "Interest penalty on premature withdrawal")),
        """## Tenure and amount
Fixed deposits can be opened for any tenure from {fd_min_tenure_days} to {fd_max_tenure_years}, with a minimum amount of {fd_min_amount}.

## Premature withdrawal
If a deposit is withdrawn early, interest is paid at the rate for the period actually held, minus {fd_premature_penalty_percent}."""),
    DocSpec("P39", "kyc-updation", "general", "KYC Updation",
        ("KYC", "re-KYC", "केवाईसी", "kyc update", "documents"),
        (F("rekyc_high_risk_years", 2, "years", "Re-KYC interval, high-risk customers"),
         F("rekyc_medium_risk_years", 8, "years", "Re-KYC interval, medium-risk customers"),
         F("rekyc_low_risk_years", 10, "years", "Re-KYC interval, low-risk customers")),
        """## How often
KYC details must be updated at least once every {rekyc_high_risk_years} for high-risk customers, every {rekyc_medium_risk_years} for medium-risk customers, and every {rekyc_low_risk_years} for low-risk customers.

## How
If there is no change in details, customers can confirm through the app or by email from the registered address. A change of address needs a valid address proof."""),
    DocSpec("P40", "contact-details-update", "general", "Updating Mobile Number and Email",
        ("mobile number", "email", "contact update", "मोबाइल नंबर बदलें", "number change"),
        (F("contact_update_effective_days", 1, "days_working", "Time for a contact change to take effect"),
         F("contact_change_transfer_cooling_hours", 24, "hours", "Hold on adding beneficiaries after a mobile number change")),
        """## Verification
Changing the registered mobile number or email requires one-time password verification. The change takes effect within {contact_update_effective_days}.

## Safety hold
For {contact_change_transfer_cooling_hours} after a mobile number change, new beneficiaries cannot be added. This protects customers if someone else changed the number."""),
)




def render_doc(doc: DocSpec) -> tuple[str, list[dict]]:
    """Return (markdown text, fact records) for one document."""
    rendered = {f.key: render_value(f.value, f.unit) for f in doc.facts}
    body = doc.body.format_map(rendered)
    keywords = list(dict.fromkeys(list(doc.keywords) + CATEGORY_KEYWORDS[doc.category]))
    text = (
        "---\n"
        f"doc_id: {doc.doc_id}\n"
        f"slug: {doc.slug}\n"
        f"category: {doc.category}\n"
        f"title: {doc.title}\n"
        f"keywords: {', '.join(keywords)}\n"
        f"effective_date: {EFFECTIVE_DATE}\n"
        "---\n"
        f"# {doc.title}\n\n{body}\n\n{FOOTER}\n"
    )
    facts = [
        {
            "fact_id": f"{doc.doc_id}.{f.key}",
            "doc_id": doc.doc_id,
            "key": f.key,
            "value": f.value,
            "unit": f.unit,
            "rendered": rendered[f.key],
            "description": f.description,
        }
        for f in doc.facts
    ]
    return text, facts


def fact_value(key: str):
    """Look up a fact value by key (used by the world generator for fees)."""
    for d in DOCS:
        for f in d.facts:
            if f.key == key:
                return f.value
    raise KeyError(key)
