import tempfile
from django.urls import reverse
from django.utils import timezone
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from vitrina.cms.models import LearningMaterial, LearningMaterialFile


class LearningMaterialFileModelTest(TestCase):
    def setUp(self):
        self.learning_material = LearningMaterial.objects.create(
            topic="Test Topic",
            published=timezone.now(),
            version=1,
        )

    def test_file_upload_with_custom_name(self):
        test_file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")

        file_obj = LearningMaterialFile.objects.create(
            learning_material=self.learning_material, file=test_file, name="Custom Name"
        )

        self.assertEqual(file_obj.name, "Custom Name")
        self.assertTrue(file_obj.file.name.startswith("learning-material-files/"))
        self.assertIsNotNone(file_obj.uploaded_at)

    def test_file_upload_without_custom_name(self):
        test_file = SimpleUploadedFile("document.pdf", b"content")

        file_obj = LearningMaterialFile.objects.create(learning_material=self.learning_material, file=test_file)

        self.assertEqual(file_obj.name, "")
        self.assertTrue(file_obj.file.name.startswith("learning-material-files/document"))
        self.assertTrue(file_obj.file.name.endswith(".pdf"))

    def test_files_relationship(self):
        test_file = SimpleUploadedFile("test.pdf", b"content")

        file_obj = LearningMaterialFile.objects.create(learning_material=self.learning_material, file=test_file)

        self.assertIn(file_obj, self.learning_material.files.all())
        self.assertEqual(self.learning_material.files.count(), 1)

    def test_cascade_deletion(self):
        test_file = SimpleUploadedFile("test.pdf", b"content")
        file_obj = LearningMaterialFile.objects.create(learning_material=self.learning_material, file=test_file)
        file_id = file_obj.id

        self.learning_material.delete()

        self.assertFalse(LearningMaterialFile.objects.filter(id=file_id).exists())


class FileExtensionTest(TestCase):
    def setUp(self):
        self.learning_material = LearningMaterial.objects.create(topic="Test", published=timezone.now(), version=1)

    def test_file_extensions(self):
        extensions = {
            "document.pdf": ".pdf",
            "document.doc": ".doc",
            "document.docx": ".docx",
            "spreadsheet.xls": ".xls",
            "spreadsheet.xlsx": ".xlsx",
            "presentation.ppt": ".ppt",
            "presentation.pptx": ".pptx",
            "archive.zip": ".zip",
            "archive.rar": ".rar",
            "image.jpg": ".jpg",
            "image.png": ".png",
            "image.gif": ".gif",
            "unknown.txt": ".txt",
        }

        for filename, expected_ext in extensions.items():
            test_file = SimpleUploadedFile(filename, b"content")
            file_obj = LearningMaterialFile.objects.create(learning_material=self.learning_material, file=test_file)

            self.assertTrue(file_obj.file.name.endswith(expected_ext))
            file_obj.delete()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FileDownloadTest(TestCase):
    def setUp(self):
        self.learning_material = LearningMaterial.objects.create(topic="Test", published=timezone.now(), version=1)

    def test_file_url_generation(self):
        test_file = SimpleUploadedFile("test.pdf", b"content")
        file_obj = LearningMaterialFile.objects.create(
            learning_material=self.learning_material, file=test_file, name="Test Document"
        )

        self.assertTrue(file_obj.file.url)
        self.assertIn("learning-material-files/", file_obj.file.url)

    def test_file_size(self):
        test_file = SimpleUploadedFile("test.pdf", b"test content")
        file_obj = LearningMaterialFile.objects.create(learning_material=self.learning_material, file=test_file)

        self.assertGreater(file_obj.file.size, 0)


class AdminInlineTest(TestCase):
    def test_inline_configuration(self):
        from vitrina.cms.admin import LearningMaterialFileInline

        self.assertEqual(LearningMaterialFileInline.model, LearningMaterialFile)
        self.assertEqual(LearningMaterialFileInline.extra, 1)
        self.assertEqual(LearningMaterialFileInline.fields, ("file", "name"))


class TemplateContextTest(TestCase):
    def setUp(self):
        self.learning_material = LearningMaterial.objects.create(
            topic="Test Material",
            description="<p>Test description</p>",
            author_name="Test Author",
            published=timezone.now(),
            video_url="dQw4w9WgXcQ",
            version=1,
        )

    def test_basic_context(self):
        self.assertEqual(self.learning_material.topic, "Test Material")
        self.assertEqual(self.learning_material.author_name, "Test Author")
        self.assertTrue(self.learning_material.published)
        self.assertEqual(self.learning_material.video_url, "dQw4w9WgXcQ")

    def test_files_in_context(self):
        test_file = SimpleUploadedFile("test.pdf", b"content")
        LearningMaterialFile.objects.create(learning_material=self.learning_material, file=test_file, name="Test File")

        self.assertEqual(self.learning_material.files.count(), 1)
        self.assertEqual(self.learning_material.files.first().name, "Test File")


class EdgeCaseTest(TestCase):
    def setUp(self):
        self.learning_material = LearningMaterial.objects.create(
            topic="Test",
            published=timezone.now(),
            version=1,
        )

    def test_empty_file(self):
        empty_file = SimpleUploadedFile("empty.pdf", b"")
        file_obj = LearningMaterialFile.objects.create(learning_material=self.learning_material, file=empty_file)

        self.assertEqual(file_obj.file.size, 0)

    def test_long_custom_name(self):
        test_file = SimpleUploadedFile("test.pdf", b"content")
        long_name = "x" * 300

        file_obj = LearningMaterialFile.objects.create(
            learning_material=self.learning_material, file=test_file, name=long_name
        )

        # Should either truncate or handle gracefully
        self.assertIsNotNone(file_obj.name)

    def test_special_characters_in_filename(self):
        filenames = [
            "file with spaces.pdf",
            "file-with-dashes.pdf",
            "file_with_underscores.pdf",
            "file(with)parentheses.pdf",
        ]

        for filename in filenames:
            test_file = SimpleUploadedFile(filename, b"content")
            file_obj = LearningMaterialFile.objects.create(learning_material=self.learning_material, file=test_file)
            self.assertIsNotNone(file_obj.file.name)
            file_obj.delete()


class IntegrationTest(TestCase):
    def test_complete_workflow(self):
        # Create learning material
        material = LearningMaterial.objects.create(
            topic="Integration Test",
            description="<p>Complete test</p>",
            author_name="Tester",
            published=timezone.now(),
            version=1,
        )

        # Add files
        files_data = [
            ("document.pdf", "PDF Document"),
            ("spreadsheet.xlsx", "Excel File"),
            ("presentation.pptx", ""),  # No custom name
        ]

        for filename, custom_name in files_data:
            test_file = SimpleUploadedFile(filename, b"content")
            LearningMaterialFile.objects.create(learning_material=material, file=test_file, name=custom_name)

        # Verify everything works together
        self.assertEqual(material.files.count(), 3)

        pdf_file = material.files.filter(name="PDF Document").first()
        self.assertIsNotNone(pdf_file)
        self.assertTrue(pdf_file.file.url)

        ppt_file = material.files.filter(name="").first()
        self.assertIsNotNone(ppt_file)
        self.assertTrue(ppt_file.file.name.endswith(".pptx"))


class DescriptionSanitizationTest(TestCase):
    def test_description_script_is_escaped_in_detail_page(self):
        material = LearningMaterial.objects.create(
            topic="Test",
            description="<p>Safe <strong>text</strong></p><script>alert(1)</script>",
            published=timezone.now(),
            version=1,
        )

        response = self.client.get(reverse("learning-material-detail", args=[material.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")
        self.assertContains(response, "<strong>text</strong>")
