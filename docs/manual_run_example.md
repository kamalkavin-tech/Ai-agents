# Manual run example

```powershell
.\venv\Scripts\python.exe main.py checkout-service "Error rate exceeded 5% threshold at 2026-08-19T22:20:00Z"
```

Expected investigation characteristics:

- Queries the checkout error-rate metric around 22:20 UTC.
- Finds payment gateway timeout errors beginning after the 22:10 deployment.
- Inspects commit `d9a3b45`.
- Connects the 3-second timeout to the failures without blaming unrelated deploys.
- Retrieves similar incident `INC-0091`.
- Recommends an approval-gated restoration of the prior timeout.

Do not treat exact prose as the golden answer. The regression evaluator checks
the evidence and behavior that make the conclusion trustworthy.
