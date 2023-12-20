import traceback
import unittest

from scripts.upload_data_to_storage import handle_error


class TestHandleError(unittest.TestCase):

    def test_handle_error(self):
        try:
            raise ValueError("Oh no")
        except ValueError as e:
            tb = traceback.format_exc()

        result = handle_error(tb)
        self.assertEqual(result, "ValueError: Oh no")


if __name__ == "__main__":
    unittest.main()
