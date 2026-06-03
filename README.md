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

## Streamlit

```bash
streamlit run app/streamlit_app.py
```

Upload a LINE `.txt` export in the app to run the same analysis without saving the raw chat into the repository.

## Notes

Charts use Matplotlib with automatic CJK font selection. On Linux, install a CJK font such as `fonts-noto-cjk` if Chinese text appears as boxes.

## Development

Run tests:

```bash
pytest tests/ -v
```

