import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'analytics'))
from calculations import summarize
class AnalyticsTests(unittest.TestCase):
    def test_example(self):
        self.assertEqual(summarize([10,20,30,40,50]), {'count':5,'minimum':10,'maximum':50,'average':30})
    def test_empty(self):
        self.assertEqual(summarize([]),{'count':0,'minimum':None,'maximum':None,'average':None})
    def test_negative(self):
        self.assertEqual(summarize([-5,5]),{'count':2,'minimum':-5,'maximum':5,'average':0})
if __name__=='__main__':unittest.main()
