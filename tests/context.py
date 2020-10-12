import os
import sys
from pathlib import Path

import gtfs_kit as gk

sys.path.insert(0, os.path.abspath('..'))


DATA_DIR = Path('gtfs_map_matcher/data')
test_feed = gk.read_feed(DATA_DIR/'auckland_gtfs_sample.zip',
  dist_units='km')
