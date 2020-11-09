from gtfs_traversal.string_shortener import StringShortener

import unittest


class TestStringShortener(unittest.TestCase):
    def prepare_subject(self):
        subject = StringShortener()

        subject._shorten_dict = {
            'abc': '0',
            'def': '1',
        }
        subject._lengthen_dict = {
            '0': 'abc',
            '1': 'def',
        }
        return subject

    def test_lengthen(self):
        subject = self.prepare_subject()
        self.assertEqual(subject.lengthen('0'), 'abc')
        self.assertEqual(subject.lengthen('1'), 'def')

    def test_shorten(self):
        subject = self.prepare_subject()
        self.assertEqual(subject.shorten('abc'), '0')
        self.assertEqual(subject.shorten('def'), '1')
        self.assertEqual(subject.shorten('ghi'), '2')

    def test_shorten_with_empty_subject(self):
        subject = StringShortener()
        self.assertEqual(subject.shorten('new string'), '0')
