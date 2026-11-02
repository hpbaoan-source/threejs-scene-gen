"""Unit tests for the deterministic parts: HTML extraction, static gates, JSON parsing.

Run:  python3 -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scene_gen.extract import (  # noqa: E402
    extract_html,
    has_canvas,
    has_three,
    looks_like_scene,
    parse_json_block,
    static_gates,
)
from scene_gen.pipeline import slugify  # noqa: E402
from scene_gen.review import parse_review  # noqa: E402
from scene_gen.render import frame_gates  # noqa: E402

MINIMAL = """<!DOCTYPE html>
<html><head><title>t</title></head>
<body><canvas id="c"></canvas>
<script type="module">
import * as THREE from "https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/three.module.min.js";
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, 16 / 9, 0.1, 100);
camera.position.set(4, 3, 6);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(1280, 720);
renderer.shadowMap.enabled = true;
document.getElementById("c").appendChild(renderer.domElement);
const hemi = new THREE.HemisphereLight(0xffffff, 0x223344, 1.2);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xffffff, 2.0);
sun.position.set(5, 10, 7);
sun.castShadow = true;
scene.add(sun);
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(60, 60),
  new THREE.MeshStandardMaterial({ color: 0x556677, roughness: 0.95 })
);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);
const cube = new THREE.Mesh(
  new THREE.BoxGeometry(1.6, 1.6, 1.6),
  new THREE.MeshStandardMaterial({ color: 0xcc5544, roughness: 0.4, metalness: 0.1 })
);
cube.position.y = 0.8;
cube.castShadow = true;
scene.add(cube);
function resize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}
window.addEventListener("resize", resize);
let dragging = false;
let lastX = 0;
let lastY = 0;
renderer.domElement.addEventListener("pointerdown", (e) => {
  dragging = true;
  lastX = e.clientX;
  lastY = e.clientY;
});
window.addEventListener("pointerup", () => {
  dragging = false;
});
window.addEventListener("pointermove", (e) => {
  if (!dragging) return;
  camera.position.x += (e.clientX - lastX) * 0.01;
  camera.position.z += (e.clientY - lastY) * 0.01;
  lastX = e.clientX;
  lastY = e.clientY;
  camera.lookAt(0, 0.8, 0);
});
function animate() {
  requestAnimationFrame(animate);
  cube.rotation.y += 0.005;
  renderer.render(scene, camera);
}
animate();
</script>
</body></html>"""


class TestExtract(unittest.TestCase):
    def test_extract_raw_document(self):
        self.assertEqual(extract_html("blah " + MINIMAL + " tail"), MINIMAL)

    def test_extract_from_fence(self):
        text = "Here you go:\n```html\n" + MINIMAL + "\n```\nDone."
        self.assertEqual(extract_html(text), MINIMAL)

    def test_extract_returns_none_without_html(self):
        self.assertIsNone(extract_html("I cannot help with that."))
        self.assertIsNone(extract_html(""))

    def test_extract_prefers_fenced_document(self):
        text = "```html\n" + MINIMAL + "\n```\n" + MINIMAL
        self.assertEqual(extract_html(text), MINIMAL)


class TestStaticGates(unittest.TestCase):
    def test_clean_file_passes(self):
        self.assertEqual(static_gates(MINIMAL), [])

    def test_missing_canvas_is_reported(self):
        problems = static_gates("<html><body><p>no canvas</p></body></html>")
        self.assertTrue(any("canvas" in p for p in problems))

    def test_unbalanced_script_is_reported(self):
        broken = MINIMAL.replace("</script>", "")
        problems = static_gates(broken)
        self.assertTrue(any("script" in p for p in problems))

    def test_empty_is_reported(self):
        self.assertTrue(static_gates(""))
        self.assertTrue(static_gates(None))

    def test_canvas_created_in_javascript_counts(self):
        js_canvas = MINIMAL.replace(
            '<canvas id="c"></canvas>',
            '<div id="c"></div>',
        ).replace(
            'document.getElementById("c").appendChild(renderer.domElement);',
            'const el = document.createElement("canvas");\n'
            'document.getElementById("c").appendChild(el);',
        )
        self.assertNotIn("<canvas", js_canvas.lower())
        self.assertTrue(has_canvas(js_canvas))
        self.assertEqual(static_gates(js_canvas), [])
        self.assertTrue(looks_like_scene(js_canvas))

    def test_renderer_owned_canvas_counts(self):
        # the most common shape: the renderer creates its own canvas and the
        # scene appends renderer.domElement to the page
        renderer_canvas = MINIMAL.replace(
            '<canvas id="c"></canvas>',
            '<div id="c"></div>',
        )
        self.assertNotIn("<canvas", renderer_canvas.lower())
        self.assertTrue(has_canvas(renderer_canvas))
        self.assertEqual(static_gates(renderer_canvas), [])

    def test_three_import_detection(self):
        self.assertTrue(has_three(MINIMAL))
        self.assertFalse(has_three("<html><body>no three here</body></html>"))
        self.assertFalse(looks_like_scene("<html><body>prose</body></html>"))


class TestJsonBlock(unittest.TestCase):
    def test_plain_json(self):
        self.assertEqual(parse_json_block('{"a": 1}'), {"a": 1})

    def test_fenced_json(self):
        self.assertEqual(parse_json_block('```json\n{"a": 2}\n```'), {"a": 2})

    def test_json_with_prose(self):
        self.assertEqual(parse_json_block('Here it is: {"a": 3} thanks'), {"a": 3})

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            parse_json_block("not json at all")


class TestReviewParsing(unittest.TestCase):
    def test_normalises_verdict(self):
        review = parse_review({"verdict": "PASS", "score": 9, "issues": ["a"], "fixes": ["b"]})
        self.assertEqual(review["verdict"], "pass")
        self.assertEqual(review["score"], 9)
        self.assertEqual(review["issues"], ["a"])

    def test_unknown_verdict_becomes_needs_work(self):
        review = parse_review({"verdict": "great", "score": 10})
        self.assertEqual(review["verdict"], "needs_work")

    def test_score_is_clamped(self):
        self.assertEqual(parse_review({"score": 99})["score"], 10)
        self.assertEqual(parse_review({"score": -5})["score"], 0)

    def test_non_dict_is_handled(self):
        review = parse_review("nonsense")
        self.assertEqual(review["verdict"], "needs_work")


class TestFrameGates(unittest.TestCase):
    def test_dark_frame_is_caught(self):
        report = {"image": {"meanLuma": 0.01, "stdLuma": 0.2}}
        problems = frame_gates(report)
        self.assertTrue(any("qua toi" in p for p in problems))

    def test_flat_frame_is_caught(self):
        report = {"image": {"meanLuma": 0.5, "stdLuma": 0.001}}
        problems = frame_gates(report)
        self.assertTrue(any("phang" in p for p in problems))

    def test_good_frame_passes(self):
        report = {"image": {"meanLuma": 0.35, "stdLuma": 0.18}}
        self.assertEqual(frame_gates(report), [])

    def test_missing_image_is_caught(self):
        self.assertTrue(frame_gates({"image": None}))


class TestSlug(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("A Japanese Village!"), "a-japanese-village")
        self.assertEqual(slugify(""), "scene")


if __name__ == "__main__":
    unittest.main()
