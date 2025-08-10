from __future__ import annotations
from pathlib import Path
import pandas as pd
from typing import List
from jinja2 import Template

HTML = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>AI Eval Report</title></head>
<body>
<h1>AI Eval Report</h1>
<p>Total questions: {{ total }}</p>
{% for prov, dfp in groups %}
  <h2>{{ prov }}</h2>
  <p>Models: {{ ", ".join(dfp.model.unique().tolist()) }}</p>
  <p>Average score: {{ "%.3f"|format(dfp.score.mean()) }}</p>
  <table border="1" cellspacing="0" cellpadding="4">
    <tr><th>qid</th><th>model</th><th>score</th><th>justification</th></tr>
    {% for _,row in dfp.sort_values(["model","qid"]).iterrows() %}
      <tr><td>{{ row.qid }}</td><td>{{ row.model }}</td><td>{{ "%.3f"|format(row.score) }}</td><td>{{ row.justification[:200] }}</td></tr>
    {% endfor %}
  </table>
{% endfor %}
</body>
</html>
"""

def emit_report(csv_path: Path, html_path: Path):
    df = pd.read_csv(csv_path)
    groups = []
    for prov, g in df.groupby("provider"):
        groups.append((prov, g))
    tpl = Template(HTML)
    html = tpl.render(total=df.qid.nunique(), groups=groups)
    html_path.write_text(html, encoding="utf-8")
