"""Build deterministic static Noto Sans HK instances for ReportLab.

This maintainer-only script reads the installed NotoSansHK variable font and
writes three static assets.  Runtime PDF export never needs fontTools.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


SANS_WEIGHTS = {
    "Regular": 400,
    "Medium": 500,
    "SemiBold": 600,
}
SERIF_WEIGHTS = {"Regular": 400, "SemiBold": 600}


def build_family(
    source: Path,
    output_dir: Path,
    *,
    family: str,
    stem: str,
    weights: dict[str, int],
    save_ttf: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for style, weight in weights.items():
        variable = TTFont(source)
        static = instantiateVariableFont(variable, {"wght": weight}, inplace=False)
        postscript = f"{stem}-{style}"
        for platform_id, encoding_id, language_id in ((3, 1, 0x409), (1, 0, 0)):
            static["name"].setName(family, 1, platform_id, encoding_id, language_id)
            static["name"].setName(style, 2, platform_id, encoding_id, language_id)
            static["name"].setName(f"{family} {style}", 4, platform_id, encoding_id, language_id)
            static["name"].setName(postscript, 6, platform_id, encoding_id, language_id)
            static["name"].setName(family, 16, platform_id, encoding_id, language_id)
            static["name"].setName(style, 17, platform_id, encoding_id, language_id)
        static["OS/2"].usWeightClass = weight
        if save_ttf:
            static.save(output_dir / f"{postscript}.ttf")
        static.flavor = "woff2"
        static.save(output_dir / f"{postscript}.woff2")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(r"C:\Windows\Fonts\NotoSansHK-VF.ttf"))
    parser.add_argument("--serif-source", type=Path, default=Path(r"C:\Windows\Fonts\NotoSerifHK-VF.ttf"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "nicegui_app" / "assets" / "fonts",
    )
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit(f"Noto Sans HK variable font not found: {args.source}")
    build_family(
        args.source,
        args.output_dir,
        family="Noto Sans HK",
        stem="NotoSansHK",
        weights=SANS_WEIGHTS,
        save_ttf=True,
    )
    if args.serif_source.is_file():
        build_family(
            args.serif_source,
            args.output_dir,
            family="Noto Serif HK",
            stem="NotoSerifHK",
            weights=SERIF_WEIGHTS,
            save_ttf=False,
        )


if __name__ == "__main__":
    main()
