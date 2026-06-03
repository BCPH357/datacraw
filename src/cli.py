"""Command-line entry point for LINE persona analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import clustering, features, parser, report, roles, viz, webreport


def run_analysis(input_path: str | Path, output_dir: str | Path = "outputs", web: bool = False) -> dict:
    """Run the full analysis pipeline and write outputs."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    parsed = parser.parse_file(input_path)
    records = parser.to_dataframe(parsed)
    summary = parser.summarize(parsed)
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    feature_frame = features.extract_features(records, output / "features.csv")
    clustered, metadata = clustering.cluster_users(feature_frame, output / "clusters.csv")
    role_table = roles.assign_roles(clustered)
    user_roles = roles.roles_by_user(clustered, role_table)
    personas = report.build_personas(user_roles, output / "personas.json")
    group_health = report.build_group_health(user_roles, metadata, output / "group_health.json")
    charts = viz.generate_all(records, feature_frame, clustered, user_roles, output) if not records.empty else []

    web_report_path = None
    if web:
        app_data = webreport.build_app_data(
            records, feature_frame, clustered, user_roles, group_health, metadata, summary
        )
        html = webreport.render_html(app_data, embedded=True)
        web_report_path = output / "web" / "index.html"
        web_report_path.parent.mkdir(parents=True, exist_ok=True)
        web_report_path.write_text(html, encoding="utf-8")

    return {
        "summary": summary,
        "metadata": metadata,
        "personas": personas,
        "group_health": group_health,
        "charts": [str(path) for path in charts],
        "web_report": str(web_report_path) if web_report_path else None,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(description="Analyze a LINE chat export.")
    arg_parser.add_argument("input_path", help="Path to LINE .txt export")
    arg_parser.add_argument("--output-dir", default="outputs", help="Output directory")
    arg_parser.add_argument(
        "--web",
        action="store_true",
        help="Also write a self-contained HTML report to <output-dir>/web/index.html",
    )
    return arg_parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = run_analysis(args.input_path, args.output_dir, web=args.web)
    print(json.dumps(
        {
            "summary": result["summary"],
            "group_health": result["group_health"],
            "web_report": result["web_report"],
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()

