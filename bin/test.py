#!/usr/bin/env python3

import unittest
import sys
from unittests.configure_projects_website_tests import *
from unittests.scan_projects_for_website_tests import *
from unittests.build_tests import *

if __name__ == '__main__':
    py = unittest.main()
    sys.exit(py)
