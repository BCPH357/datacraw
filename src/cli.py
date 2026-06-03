"""Command-line entry point for LINE persona analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import clustering, features, parser, report, roles, viz


def run_analysis(input_path: str | Path, output_dir: str | Path = "outputs") -> dict:
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

    return {
        "summary": summary,
        "metadata": metadata,
        "personas": personas,
        "group_health": group_health,
        "charts": [str(path) for path in charts],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(description="Analyze a LINE chat export.")
    arg_parser.add_argument("input_path", help="Path to LINE .txt export")
    arg_parser.add_argument("--output-dir", default="outputs", help="Output directory")
    return arg_parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = run_analysis(args.input_path, args.output_dir)
    print(json.dumps({"summary": result["summary"], "group_health": result["group_health"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

