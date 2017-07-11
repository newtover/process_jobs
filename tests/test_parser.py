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
