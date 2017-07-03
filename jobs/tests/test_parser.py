from unittest import TestCase
from jobs.parser import iter_n_grams

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
        self.assertEqual([('a',), ('b',), ('a', 'b'), ('c',), ('a', 'b', 'c'), ('b', 'c')],
                         list(iter_n_grams(text, 3)))
