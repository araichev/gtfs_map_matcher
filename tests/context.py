import os
import sys
from pathlib import Path

import gtfstk

sys.path.insert(0, os.path.abspath('..'))


DATA_DIR = Path('data')
welly_feed = gtfstk.read_gtfs(DATA_DIR/'wellington_gtfs_20171016.zip',
  dist_units='km')
