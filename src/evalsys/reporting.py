from __future__ import annotations
from pathlib import Path
import pandas as pd
from typing import List
from jinja2 import Template

HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>AI Eval Report</title>
<style>
  body { font-family: Arial, sans-serif; margin: 20px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
  th, td { border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }
  th { background-color: #f2f2f2; font-weight: bold; }
  .justification { max-width: 600px; word-wrap: break-word; }
  .score { text-align: center; font-weight: bold; }
  .qid { text-align: center; }
  .model { font-weight: bold; }
  h2 { color: #333; border-bottom: 2px solid #ddd; padding-bottom: 5px; }
</style>
</head>
<body>
<h1>AI Eval Report</h1>
<p>Total questions: {{ total }}</p>
{% for model_name, dfm in groups %}
  <h2>{{ model_name }}</h2>
  <p>Provider: {{ dfm.provider.iloc[0] }}</p>
  <p>Average score: {{ "%.3f"|format(dfm.score.mean()) }}</p>
  <table>
    <tr><th class="qid">Question ID</th><th class="score">Score</th><th class="justification">Justification</th></tr>
    {% for _,row in dfm.sort_values(["qid"]).iterrows() %}
      <tr>
        <td class="qid">{{ row.qid }}</td>
        <td class="score">{{ "%.3f"|format(row.score) }}</td>
        <td class="justification">{{ row.justification }}</td>
      </tr>
    {% endfor %}
  </table>
{% endfor %}
</body>
</html>
"""

def emit_report(csv_path: Path, html_path: Path):
    df = pd.read_csv(csv_path)
    groups = []
    for model, g in df.groupby("model"):
        groups.append((model, g))
    tpl = Template(HTML)
    html = tpl.render(total=df.qid.nunique(), groups=groups)
    html_path.write_text(html, encoding="utf-8")
