import sys
import unittest
import os
import re

from fara import scrape, parse_and_save

class test_results(unittest.TestCase):
	def test_content(self):
		## build test here
