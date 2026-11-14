# Evidence directory

No benchmark results have been generated in this ZIP. Once EKS is running:

1. Start `kubectl -n acit3495 port-forward svc/enter-data 5000:5000` in one terminal.
2. Run `python scripts/run_experiments.py` from the project root in another terminal.
3. Run `python scripts/summarize_results.py` and `python scripts/create_report.py`; put screenshots alongside the generated files.
4. Run `python scripts/create_presentation.py` again to add numeric results to the presentation.

`*.json`, `*.csv`, and `*.log` from the experiment are raw grading evidence. Do not edit or fabricate them. Avoid screenshots that show your demo password or any cloud credentials. The program never puts the demo password in logs or exported charts.
