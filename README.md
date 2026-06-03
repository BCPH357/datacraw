# LINE Chat Persona Analyzer

Analyze exported LINE group chats and generate participant features, clusters, role summaries, group health metrics, and visual reports.

## Setup

Create the conda environment:

```bash
conda env create -f environment.yml
conda activate datacraw-line-persona
```

Or install into an existing Python 3.11+ environment:

```bash
pip install -r requirements.txt
```

## Privacy

Raw LINE exports can contain personal data. Put them under `data/raw/`; this folder is ignored by git. Generated reports and charts go under `outputs/`, which is also ignored.

## CLI

```bash
python -m src.cli data/raw/your_line_export.txt --output-dir outputs
```

Generated files include:

- `features.csv`
- `clusters.csv`
- `personas.json`
- `group_health.json`
- PNG charts under `outputs/`

Add `--web` to also produce a self-contained interactive HTML report:

```bash
python -m src.cli data/raw/your_line_export.txt --web
```

This writes `outputs/web/index.html` — the React editorial report (the same
design as the Streamlit app) with your real data baked in. Open it in any
browser. It loads React/Babel from a CDN, so an internet connection is needed
the first time it renders.

## Web server (upload → live report)

```bash
python app/server.py --port 8000      # then open http://127.0.0.1:8000
```

This serves the React app starting at the **upload screen**. Drop a LINE `.txt`
(or click "使用範例資料" for the bundled sample); the file is POSTed to
`/analyze`, the backend runs the full pipeline, and the same single-page app
renders the **main report screen** from the returned data — no page reload, and
nothing is written to disk. Use "↺ 重新分析" in the sidebar to analyse another
file. React/Babel load from a CDN, so the browser needs internet on first load.

Endpoints: `GET /` (upload page), `GET /app/<asset>` (jsx/css), `POST /analyze`
(multipart `file` → `APP_DATA` JSON), `GET /sample` (analyse the bundled fixture).

## Streamlit (interactive report)

```bash
streamlit run app/streamlit_app.py
```

Upload a LINE `.txt` export in the app. Streamlit runs the full pipeline
(parser → features → clustering → roles → report) and renders the **editorial
persona report** (overview, member cast, per-member profile cards, and the
visualisation room) embedded full-height, driven entirely by your real data.
The raw chat is never written into the repository, and the report HTML plus
`personas.json` / `group_health.json` can be downloaded from the app.

### How the UI is wired

The front-end is a React single-page report that reads a global
`window.APP_DATA`. `claude_design/index.html` is its canonical entry harness
(the CDN React/Babel setup) and `claude_design/app/` holds the components
(`*.jsx`) and styles.

`src/webreport.py` is the bridge: `build_app_data` maps pipeline outputs into
the `APP_DATA` schema (members, radar stats, role/health metrics, real 24-hour
activity heatmap, PCA scatter, hall-of-fame and observations are derived
deterministically from the data). `render_html` then takes
`claude_design/index.html` as a template, inlines the stylesheet and JSX, and
replaces the demo `app/data.js` with the real injected data — producing the
self-contained HTML used by both the CLI `--web` export and the Streamlit embed.

To run the original design demo (fake sample data) standalone, serve the folder
over HTTP (Babel fetches the `.jsx` files, which `file://` blocks):

```bash
cd claude_design && python -m http.server 8000   # then open http://localhost:8000
```

## Notes

Charts use Matplotlib with automatic CJK font selection. On Linux, install a CJK font such as `fonts-noto-cjk` if Chinese text appears as boxes.

## Development

Run tests:

```bash
pytest tests/ -v
```

