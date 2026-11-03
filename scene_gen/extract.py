"""HTML extraction, static gates, and JSON parsing helpers.

These are the deterministic checks that run BEFORE a browser render is
attempted, so no model tokens are spent on code that is already broken.
"""
import json
import re

HTML_PATTERNS = (
    re.compile(r"<!DOCTYPE html.*?</html>", re.S | re.I),
    re.compile(r"<html.*?</html>", re.S | re.I),
)


def extract_html(text):
    """Pull a full HTML document out of a model response.

    Handles a fenced ```html block first (models often wrap the file), then
    falls back to a raw document in the text.
    """
    if not text:
        return None
    fence = re.search(r"```(?:html|HTML)?[ \t]*\n?(.*?)```", text, re.S)
    if fence:
        inner = fence.group(1)
        if "<html" in inner.lower():
            for pattern in HTML_PATTERNS:
                match = pattern.search(inner)
                if match:
                    return match.group(0)
    for pattern in HTML_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def parse_json_block(text):
    """Parse JSON from a model response, tolerating fences and stray prose."""
    if not text:
        raise ValueError("empty response")
    candidates = []
    fence = re.search(r"```(?:json)?[ \t]*\n?(.*?)```", text, re.S)
    if fence:
        candidates.append(fence.group(1))
    candidates.append(text)
    brace = re.search(r"\{.*\}", text, re.S)
    if brace:
        candidates.append(brace.group(0))
    for candidate in candidates:
        try:
            return json.loads(candidate.strip())
        except (ValueError, TypeError):
            continue
    raise ValueError("khong parse duoc JSON tu response")


def has_canvas(html):
    """True when the scene has something to draw on.

    Three.js scenes reach a canvas in three different ways and all of them
    are legitimate:
      * a `<canvas>` tag in the markup,
      * `document.createElement('canvas')`,
      * `new THREE.WebGLRenderer()` - the renderer creates its own canvas and
        the scene appends `renderer.domElement` to the page.
    Only the last case was missing, and it is the most common one.
    """
    if not html:
        return False
    lowered = html.lower()
    if re.search(r"<canvas\b", lowered):
        return True
    if re.search(r"createelement\(\s*['\"]canvas['\"]", lowered):
        return True
    if "webglrenderer" in lowered:
        return True
    return "renderer.domelement" in lowered


def has_three(html):
    """True when the file actually imports Three.js."""
    if not html:
        return False
    return bool(
        re.search(r"three\.(module\.)?min\.js", html, re.I)
        or re.search(r"from\s*['\"]three['\"]", html)
    )


def static_gates(html):
    """Cheap structural checks that run before spending a render.

    Returns a list of human-readable problems; an empty list means the file
    looks structurally sound enough to render.
    """
    problems = []
    if not html or not html.strip():
        return ["HTML rong"]
    if not has_canvas(html):
        problems.append("khong thay canvas - trinh duyet se khong co gi de ve")
    if "</html>" not in html.lower():
        problems.append("thieu </html> - tai lieu bi cat ngan")
    if html.lower().count("<script") != html.lower().count("</script>"):
        problems.append("the <script> khong khop - javascript se khong chay")
    if "<body" not in html.lower():
        problems.append("thieu <body>")
    if not has_three(html):
        problems.append("khong tim thay import three.js")
    if len(html) < 1500:
        problems.append(f"HTML qua ngan ({len(html)} bytes) - co the bi cat ngan")
    problems.extend(sky_shader_problems(html))
    return problems


def sky_shader_problems(html):
    """Catch a custom sky/gradient shader that skips the sRGB output step.

    Three.js converts a material's colours from linear to sRGB in the
    `colorspace_fragment` shader chunk. A hand-written ShaderMaterial that
    writes `gl_FragColor` without that chunk puts linear values straight into
    the framebuffer, so every colour in the shader comes out about one gamma
    too dark - a daytime sky renders as night. The bug is invisible in the
    code review and in the model output, so it is checked here instead.
    """
    problems = []
    if "ShaderMaterial" not in html:
        return problems
    if "gl_FragColor" not in html:
        return problems
    if "colorspace_fragment" in html:
        return problems
    problems.append(
        "ShaderMaterial tu viet gl_FragColor nhung thieu #include <colorspace_fragment> "
        "- mau se bi toi mot gamma (ban ngay ra dem)"
    )
    return problems


def looks_like_scene(html):
    """True when the file has the shape of a Three.js scene rather than prose."""
    if not html:
        return False
    return has_three(html) and (has_canvas(html) or "WebGLRenderer" in html)
