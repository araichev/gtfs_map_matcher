import os
import sys
from pathlib import Path

import gtfstk

sys.path.insert(0, os.path.abspath('..'))


DATA_DIR = Path('gtfs_map_matcher/data')
test_feed = gtfstk.read_gtfs(DATA_DIR/'auckland_gtfs_sample.zip',
  dist_units='km')
