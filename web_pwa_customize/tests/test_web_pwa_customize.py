# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import io

from PIL import Image

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged("-at_install", "post_install")
class TestWebPwaCustomize(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        icp = cls.env["ir.config_parameter"].sudo()
        icp.set_param("pwa.manifest.short_name", "SHORT-NAME")
        icp.set_param("pwa.manifest.background_color", "#2E69B5")
        icp.set_param("pwa.manifest.theme_color", "#2E69B4")
        cls.Settings = cls.env["res.config.settings"]
        cls.Attachment = cls.env["ir.attachment"]

    def create_png_base64(self, size=(512, 512), color=(255, 0, 0)):
        """Create a base64-encoded PNG image.
        :param tuple size: Image size (width, height)
        :param tuple color: RGB color
        :return: Base64-encoded PNG bytes
        """
        img = Image.new("RGB", size, color)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue())

    def create_svg_base64(self):
        """Create a base64-encoded SVG image.
        The SVG includes a proper XML header so Odoo can correctly
        detect the mimetype as ``image/svg+xml``.
        """
        svg = b"""<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg"
             width="512" height="512"
             viewBox="0 0 512 512">
            <rect width="512" height="512" fill="red"/>
        </svg>
        """
        return base64.b64encode(svg)

    def _get_pwa_attachments(self):
        """Return all PWA-related icon attachments."""
        return self.Attachment.search(
            [
                ("url", "like", "/web_pwa_customize/icon"),
            ]
        )

    def test_webmanifest_customize(self):
        response = self.url_open("/web/manifest.webmanifest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/manifest+json")
        data = response.json()
        self.assertEqual(data["short_name"], "SHORT-NAME")
        self.assertEqual(data["background_color"], "#2E69B5")
        self.assertEqual(data["theme_color"], "#2E69B4")

    def test_webmanifest_with_svg_icon(self):
        """Web manifest should expose a single SVG icon when an SVG is configured."""
        settings = self.env["res.config.settings"].create(
            {
                "pwa_icon": self.create_svg_base64(),
            }
        )
        settings.set_values()
        response = self.url_open("/web/manifest.webmanifest")
        data = response.json()
        self.assertIn(
            "icons",
            data,
            "Web manifest should contain icons when a custom SVG icon is set",
        )
        self.assertEqual(
            len(data["icons"]),
            1,
            "SVG icon should produce exactly one manifest icon entry",
        )
        self.assertIn(
            "512x512",
            data["icons"][0]["sizes"],
            "SVG icon should advertise all standard sizes including 512x512",
        )
        self.assertTrue(
            data["icons"][0]["type"].startswith("image/svg"),
            "Manifest icon mimetype should be SVG",
        )

    def test_webmanifest_with_png_icon(self):
        """Web manifest should expose resized PNG icons when a PNG is configured."""
        settings = self.env["res.config.settings"].create(
            {
                "pwa_icon": self.create_png_base64(),
            }
        )
        settings.set_values()
        response = self.url_open("/web/manifest.webmanifest")
        data = response.json()
        self.assertIn(
            "icons",
            data,
            "Web manifest should contain icons when a custom PNG icon is set",
        )
        self.assertEqual(
            len(data["icons"]),
            6,
            "PNG icon should generate 6 resized manifest icons",
        )
        sizes = {icon["sizes"] for icon in data["icons"]}
        self.assertIn(
            "512x512",
            sizes,
            "Manifest icons should include a 512x512 size for PNG icons",
        )

    def test_default_colors(self):
        """Default background and theme colors should be correctly set."""
        values = self.Settings.default_get(
            [
                "pwa_background_color",
                "pwa_theme_color",
            ]
        )
        self.assertEqual(
            values["pwa_background_color"],
            "#2E69B5",
            "Default PWA background color is incorrect",
        )
        self.assertEqual(
            values["pwa_theme_color"],
            "#2E69B4",
            "Default PWA theme color is incorrect",
        )

    def test_set_svg_icon_creates_one_attachment(self):
        """Setting an SVG icon should create exactly one attachment."""
        settings = self.Settings.create(
            {
                "pwa_icon": self.create_svg_base64(),
            }
        )
        settings.set_values()
        attachments = self._get_pwa_attachments()
        self.assertEqual(
            len(attachments),
            1,
            "SVG icon should create a single ir.attachment record",
        )
        self.assertTrue(
            attachments.mimetype.startswith("image/svg"),
            "Attachment mimetype should be SVG",
        )

    def test_set_png_icon_creates_all_sizes(self):
        """Setting a PNG icon should create original + resized attachments."""
        settings = self.Settings.create(
            {
                "pwa_icon": self.create_png_base64(),
            }
        )
        settings.set_values()
        attachments = self._get_pwa_attachments()
        self.assertEqual(
            len(attachments),
            7,
            "PNG icon should create 1 original and 6 resized attachments",
        )
        sizes = sorted(a.url.split("/")[-1] for a in attachments if "x" in a.url)
        self.assertIn(
            "icon512x512.png",
            sizes,
            "512x512 resized PNG icon is missing",
        )

    def test_get_values_loads_icon(self):
        """get_values() should load the current PWA icon from attachments."""
        settings = self.Settings.create(
            {
                "pwa_icon": self.create_svg_base64(),
            }
        )
        settings.set_values()
        values = self.Settings.get_values()
        self.assertTrue(
            values["pwa_icon"],
            "get_values() should return the stored PWA icon",
        )

    def test_reject_small_png(self):
        """PNG icons smaller than 512x512 should be rejected."""
        settings = self.Settings.create(
            {
                "pwa_icon": self.create_png_base64(size=(256, 256)),
            }
        )
        with self.assertRaises(
            UserError,
            msg="PNG icons smaller than 512x512 must raise a UserError",
        ):
            settings.set_values()

    def test_reject_invalid_mimetype(self):
        """Non-image uploads should be rejected."""
        settings = self.Settings.create(
            {
                "pwa_icon": base64.b64encode(b"not-an-image"),
            }
        )
        with self.assertRaises(
            UserError,
            msg="Invalid mimetype should raise a UserError",
        ):
            settings.set_values()

    def test_delete_icon_when_empty(self):
        """Removing the PWA icon should delete all related attachments."""
        settings = self.Settings.create(
            {
                "pwa_icon": self.create_png_base64(),
            }
        )
        settings.set_values()
        self.assertTrue(
            self._get_pwa_attachments(),
            "PWA icon attachments should exist after setting an icon",
        )
        settings.write({"pwa_icon": False})
        settings.set_values()
        self.assertFalse(
            self._get_pwa_attachments(),
            "All PWA icon attachments should be deleted when icon is removed",
        )
