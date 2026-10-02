"""#85 task-owned oracle for native owner dashboard receipts."""
import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

OBSERVATIONS = (
    "fixturePosted", "calendarBounds", "rendered", "repeatSame", "emptyDay",
    "dateRollover", "defaultYesterday", "sourceStateUnchanged", "topFive", "negativeProfit",
)
EXPECTED = {
    "revenue": "1010", "vat": "202", "grossSales": "1212", "cost": "365",
    "grossProfit": "645", "invoiceCount": "3", "averageTicket": "336.67",
    "productCount": "6",
}
PRODUCTS = (
    ("85-B", "450", "180", "270"),
    ("85-A", "300", "120", "180"),
    ("85-C", "80", "30", "50"),
    ("85-D", "70", "20", "50"),
    ("85-E", "60", "10", "50"),
    ("85-F", "50", "5", "45"),
)


def rows(path):
    result = {}
    for line in Path(path).read_bytes().decode("utf-8-sig").splitlines():
        key, sep, value = line.partition("###")
        if not sep or not key or key in result:
            raise ValueError("malformed or duplicate receipt row")
        result[key] = value
    return result


def number(text):
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("invalid numeric receipt") from exc
    if not value.is_finite():
        raise ValueError("non-finite numeric receipt")
    return value


def validate(request, client, server):
    if set(client) != {"run", "nonce", "token", "returned", "formCreated", "complete"}:
        raise ValueError("incomplete client/form receipt")
    expected_keys = {"run", "nonce", "token", "day", "serverComplete", *OBSERVATIONS, *EXPECTED}
    expected_keys.update("product" + str(i) for i in range(1, 7))
    if set(server) != expected_keys:
        raise ValueError("incomplete server receipt")
    for record in (client, server):
        if record["run"] != request["runId"] or record["nonce"] != request["nonce"]:
            raise ValueError("stale request binding")
    if not server["token"] or server["token"] == request["nonce"] or server["token"] != client["token"]:
        raise ValueError("missing independent server witness")
    for name in OBSERVATIONS:
        if server[name] != "true":
            raise ValueError("failed native observation: " + name)
    for name in ("returned", "formCreated", "complete"):
        if client[name] != "true":
            raise ValueError("client/form not complete: " + name)
    if server["serverComplete"] != "true":
        raise ValueError("server not complete")
    from datetime import date
    try:
        day = date.fromisoformat(server["day"]).isoformat()
    except ValueError as exc:
        raise ValueError("invalid report date") from exc
    actual = {}
    for name, expected in EXPECTED.items():
        value = number(server[name])
        if value != Decimal(expected):
            raise ValueError("wrong native dashboard value: " + name)
        actual[name] = str(value)
    products = []
    for i, expected in enumerate(PRODUCTS, 1):
        row = server["product" + str(i)].split("|")
        if len(row) != 4 or row[0] != expected[0]:
            raise ValueError("wrong product rank or identity")
        if any(number(a) != Decimal(e) for a, e in zip(row[1:], expected[1:])):
            raise ValueError("wrong per-product native values")
        products.append({"name": row[0], "revenue": row[1], "cost": row[2], "grossProfit": row[3]})
    return {"status": "PASS", "businessPayload": {
        "day": day, "metrics": actual, "products": products,
        "observations": {k: True for k in OBSERVATIONS},
        "scope": "real SalesInvoice posting; production report query/render and native form creation; not interactive GUI or live trade data",
    }}


def main():
    parser = argparse.ArgumentParser()
    for name in ("request", "client-receipt", "server-receipt"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.request).read_text()), rows(args.client_receipt), rows(args.server_receipt))))


if __name__ == "__main__":
    main()
