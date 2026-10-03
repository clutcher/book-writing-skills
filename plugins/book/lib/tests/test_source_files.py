import tempfile
import unittest
from pathlib import Path

import support

from source_files import FETCH, SourceFolders, UnsafeFileKey


class OriginRecordKeyTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.book = Path(self.work.name) / "book"
        self.folders = SourceFolders(root=self.book, files=self.book / "sources" / "library",
                                     origin=self.book / "sources" / "library-index")

    def tearDown(self):
        self.work.cleanup()

    def test_should_write_the_origin_record_when_the_key_is_a_plain_file_name(self):
        # when
        path = self.folders.write_origin_record("Hal19", FETCH, {"status": "cached"})

        # then
        self.assertEqual(path, self.book / "sources" / "library-index" / "Hal19.json")
        self.assertEqual(self.folders.read_origin_record("Hal19", FETCH), {"status": "cached"})

    def test_should_refuse_the_origin_record_when_the_key_climbs_out_of_the_book(self):
        # given
        key = "../../../notes"

        # when
        with self.assertRaises(UnsafeFileKey):
            self.folders.write_origin_record(key, FETCH, {"status": "cached"})

        # then
        self.assertEqual(list(Path(self.work.name).rglob("*.json")), [])
        self.assertIsNone(self.folders.read_origin_record(key, FETCH))


if __name__ == "__main__":
    unittest.main()
