"""
Named HTML entities are much easier to comprehend than numeric entities. This
module helps convert between the more typical numerical entiies and the more
attractive named entities.
"""

# Primarily a packaging of Ian Beck's work from
# http://beckism.com/2009/03/named_entities_python/

# There are too many little differences in Python 2 and Python 3 string handling
# syntax and symantics to easily have just one implementation. So there are two
# (very similar) parallel implementations, multiplexed here.

import sys
if sys.version_info[0] >= 3:
    from namedentities3 import named_entities, encode_ampersands
else:
    from namedentities2 import named_entities, encode_ampersands
