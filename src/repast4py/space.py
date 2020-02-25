
from ._space import Grid, DiscretePoint, SharedGrid

from enum import Enum
from collections import namedtuple
import sys

class BorderType:
    Sticky = 0

class OccupancyType:
    Multiple = 0

if sys.version_info[0] == 3 and sys.version_info[1] >= 7:
    BoundingBox = namedtuple('BoundingBox', ['xmin', 'xextent', 'ymin', 'yextent', 'zmin', 'zextent'],
        defaults=[0, 0])
else:
    BoundingBox = namedtuple('BoundingBox', ['xmin', 'xextent', 'ymin', 'yextent', 'zmin', 'zextent'])




