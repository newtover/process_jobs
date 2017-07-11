from unittest import TestCase
from jobtechs.parser import iter_n_grams

class TestIterNGrams(TestCase):
    def test_unigrams(self):
        text = 'a b c'
        self.assertEqual(list(iter_n_grams(text, 1)), [('a',), ('b',), ('c',)])

    def test_bigrams(self):
        text = 'a b c'
        self.assertEqual([('a',), ('b',), ('a', 'b'), ('c',), ('b', 'c')], 
                         list(iter_n_grams(text, 2)))

    def test_trigrams(self):
        text = 'a b c'
        self.assertEqual([('a',), ('b',), ('a', 'b'), ('c',), ('b', 'c'), ('a', 'b', 'c')],
                         list(iter_n_grams(text, 3)))

    def test_dot_extraction1(self):
        text = 'a node.js developer.'
        self.assertEqual(
            [('a',), ('node.js',), ('developer',), ('',)],
            list(iter_n_grams(text, 1))
        )

    def test_dot_extraction2(self):
        text = 'a .net developer'
        self.assertEqual(
            [('a',), ('.net',), ('developer',)],
            list(iter_n_grams(text, 1))
        )

    def test_prev_separator_processing(self):
        # we want to check thet .net does not break (microsoft .net) bi-gram,
        # since prev_sep contains a \S
        text = 'microsoft .net'
        self.assertEqual(
            [('microsoft',), ('.net',), ('microsoft', '.net')],
            list(iter_n_grams(text, 2))
        )

    def test_next_separator_merging(self):
        # this should give us node.js.io as a single word
        text = 'a node.js.io file'
        self.assertEqual(
            [('a',), ('node.js.io',), ('a', 'node.js.io'), ('file',), ('node.js.io', 'file')],
            list(iter_n_grams(text, 2))
        )

    def test_next_separator_processing(self):
        # we want to check that the sympols from the next_sep do not break bi-gram,
        # since prev_sep for developer contains a \S
        text = 'c# developer'
        self.assertEqual(
            [('c#',), ('developer',), ('c#', 'developer')],
            list(iter_n_grams(text, 2))
        )
