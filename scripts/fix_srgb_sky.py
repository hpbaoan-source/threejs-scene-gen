#!/usr/bin/env python3
"""Apply the sRGB output fix to a scene that writes gl_FragColor by hand."""
import re
import sys

path = sys.argv[1]
src = open(path, encoding="utf-8").read()
if "colorspace_fragment" in src:
    print("already fixed")
    sys.exit(0)

# insert the chunk right after each gl_FragColor assignment inside a fragment shader
pattern = re.compile(r"(\n(\s*)gl_FragColor\s*=\s*vec4\([^;]*\);)")
matches = pattern.findall(src)
if not matches:
    print("no gl_FragColor assignment found")
    sys.exit(1)

new, count = pattern.subn(
    lambda m: f"{m.group(1)}\n{m.group(2)}#include <colorspace_fragment>",
    src,
)
open(path, "w", encoding="utf-8").write(new)
print(f"patched {count} gl_FragColor assignment(s) in {path}")
