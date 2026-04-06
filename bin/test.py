#!/usr/bin/env python3

import unittest
import sys
from unittests.configure_tests import *
from unittests.scan_tests import *

if __name__ == '__main__':
    py = unittest.main()
    sys.exit(py)
