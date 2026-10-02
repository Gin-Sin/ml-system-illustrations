#!/usr/bin/env python3
"""Bundle the film's typefaces and export real LaTeX as accessible web SVGs."""
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

from fontTools.ttLib import TTFont
from manim import MathTex

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets"


def main():
    fonts = ASSETS / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    families = [
        ("CMU Serif:style=Roman", "cmu-serif-regular.woff2"),
        ("CMU Serif:style=Italic", "cmu-serif-italic.woff2"),
        ("JetBrains Mono:style=Regular", "jetbrains-mono-regular.woff2"),
        ("Lato:style=Regular", "lato-regular.woff2"),
        ("Lato:style=Bold", "lato-bold.woff2"),
    ]
    for family, filename in families:
        path = subprocess.check_output(["fc-match", "-f", "%{file}", family], text=True).strip()
        font = TTFont(path)
        font.flavor = "woff2"
        font.save(fonts / filename)
    for package in ["fonts-cmu", "fonts-jetbrains-mono", "fonts-lato"]:
        notice = Path(f"/usr/share/doc/{package}/copyright").read_text()
        (fonts / f"{package}-LICENSE.txt").write_text("\n".join(line.rstrip() for line in notice.splitlines()) + "\n")
    shutil.copyfile("/usr/share/common-licenses/Apache-2.0", fonts / "Apache-2.0.txt")
    equations = [
        ("logical-block", r"\left\lfloor\frac{t}{B}\right\rfloor", "#58c4dd"),
        ("weighted-sum", r"\sum_{i=0}^{t}\alpha_i\mathbf{v}_i", "#5cd0b3"),
        ("tail-bound", r"B-1", "#ffff80"),
    ]
    for name, tex, color in equations:
        expression = MathTex(tex)
        svg = ET.parse(expression.file_name)
        svg.getroot().set("fill", color)
        svg.getroot().set("role", "img")
        svg.write(ASSETS / f"{name}.svg", encoding="unicode")
    print("Bundled narrative, interface, and code fonts; exported three LaTeX SVGs.")


if __name__ == "__main__":
    main()
