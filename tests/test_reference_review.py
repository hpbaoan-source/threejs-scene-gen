"""Unit tests for the reference-photo path: multi-image API calls and the
review/patch prompts that tell the model which image is which.

Run:  python3 -m unittest discover -s tests -v
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scene_gen.api import Client  # noqa: E402
from scene_gen.review import (  # noqa: E402
    REFERENCE_NOTE,
    build_repair_prompt,
    build_review_prompt,
    review_scene,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
JPEG = b"\xff\xd8\xff" + b"\x00" * 8


class FakeResponse:
    def __init__(self, payload):
        self.text = json.dumps(payload)
        self.output_tokens = 10
        self.input_tokens = 20
        self.thinking_tokens = 0

    def json(self):
        return json.loads(self.text)


class RecordingClient:
    """Stands in for the API client and records what was sent."""

    def __init__(self, payload=None):
        self.calls = []
        self.payload = payload or {
            "verdict": "pass",
            "score": 8,
            "scores": {},
            "issues": [],
            "fixes": [],
        }

    def complete_with_images(self, image_list, prompt, system=None, max_tokens=None, effort=None):
        self.calls.append({"images": list(image_list), "prompt": prompt})
        return FakeResponse(self.payload)

    def complete_with_image(self, image_bytes, prompt, system=None, max_tokens=None, effort=None):
        self.calls.append({"images": [image_bytes], "prompt": prompt})
        return FakeResponse(self.payload)


class TestClientBody(unittest.TestCase):
    def _body(self, images):
        client = Client(model="m", effort="low", max_tokens=128)
        captured = {}

        def fake_post(body):
            captured["body"] = body
            return {"content": [{"type": "text", "text": "{}"}], "usage": {}}

        client._post = fake_post
        client.complete_with_images(images, "hello")
        return captured["body"]

    def test_two_images_are_sent_in_order_then_text(self):
        body = self._body([PNG, JPEG])
        content = body["messages"][0]["content"]
        self.assertEqual(len(content), 3)
        self.assertEqual(content[0]["type"], "image")
        self.assertEqual(content[1]["type"], "image")
        self.assertEqual(content[2]["type"], "text")
        self.assertEqual(content[2]["text"], "hello")

    def test_media_type_follows_the_bytes(self):
        body = self._body([PNG, JPEG])
        content = body["messages"][0]["content"]
        self.assertEqual(content[0]["source"]["media_type"], "image/png")
        self.assertEqual(content[1]["source"]["media_type"], "image/jpeg")

    def test_single_image_helper_still_works(self):
        client = Client(model="m", effort="low", max_tokens=128)
        captured = {}

        def fake_post(body):
            captured["body"] = body
            return {"content": [{"type": "text", "text": "{}"}], "usage": {}}

        client._post = fake_post
        client.complete_with_image(PNG, "hi")
        content = captured["body"]["messages"][0]["content"]
        self.assertEqual(len(content), 2)
        self.assertEqual(content[0]["type"], "image")
        self.assertEqual(content[1]["text"], "hi")


class TestReviewPrompts(unittest.TestCase):
    def test_reference_note_absent_without_reference(self):
        prompt = build_review_prompt("a villa", threshold=7)
        self.assertNotIn("IMAGE 1", prompt)
        self.assertNotIn("reference photo", prompt)

    def test_reference_note_present_with_reference(self):
        prompt = build_review_prompt("a villa", threshold=7, has_reference=True)
        self.assertIn("IMAGE 1 = the reference photo", prompt)
        self.assertIn("IMAGE 2 = the current render", prompt)

    def test_repair_prompt_mentions_the_reference(self):
        prompt = build_repair_prompt(
            "a villa",
            {"score": 5, "issues": ["no pool"]},
            "<html></html>",
            has_reference=True,
        )
        self.assertIn("IMAGE 1 = the reference photo", prompt)
        self.assertIn("missing from the render but present in the reference", prompt)

    def test_repair_prompt_without_reference_has_no_image_note(self):
        prompt = build_repair_prompt("a villa", {"score": 5}, "<html></html>")
        self.assertNotIn("IMAGE 1", prompt)

    def test_reference_note_defines_both_images(self):
        self.assertIn("IMAGE 1", REFERENCE_NOTE)
        self.assertIn("IMAGE 2", REFERENCE_NOTE)


class TestReviewScene(unittest.TestCase):
    def test_sends_reference_first_then_render(self):
        client = RecordingClient()
        review_scene(
            client,
            "a villa",
            PNG,
            threshold=7,
            render_note="attempt 0",
            reference_bytes=JPEG,
        )
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["images"], [JPEG, PNG])
        self.assertIn("IMAGE 1 = the reference photo", client.calls[0]["prompt"])

    def test_sends_only_the_render_without_reference(self):
        client = RecordingClient()
        review_scene(client, "a villa", PNG, threshold=7)
        self.assertEqual(client.calls[0]["images"], [PNG])
        self.assertNotIn("IMAGE 1", client.calls[0]["prompt"])


class FlakyClient(RecordingClient):
    """Returns a non-JSON reply first, valid JSON second."""

    def __init__(self, payload=None):
        super().__init__(payload)
        self.bad_first = True

    def complete_with_images(self, image_list, prompt, system=None, max_tokens=None, effort=None):
        self.calls.append({"images": list(image_list), "prompt": prompt})
        if self.bad_first:
            self.bad_first = False
            return BadResponse("I think it looks quite good actually, nice work.")
        return FakeResponse(self.payload)


class BadResponse(FakeResponse):
    def __init__(self, text):
        super().__init__({})
        self.text = text

    def json(self):
        raise ValueError("not json")


class TestReviewRetry(unittest.TestCase):
    def test_asks_again_when_the_reply_is_not_json(self):
        client = FlakyClient()
        result = review_scene(client, "a villa", PNG, threshold=7)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("not valid JSON", client.calls[1]["prompt"])
        self.assertEqual(result["verdict"], "pass")

    def test_gives_up_after_two_bad_replies(self):
        class AlwaysBad(FlakyClient):
            def complete_with_images(self, image_list, prompt, system=None, max_tokens=None, effort=None):
                self.calls.append({"images": list(image_list), "prompt": prompt})
                return BadResponse("still not json")

        client = AlwaysBad()
        result = review_scene(client, "a villa", PNG, threshold=7)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(result["score"], 0)
        self.assertIn("review khong phai JSON", result["issues"])


if __name__ == "__main__":
    unittest.main()
