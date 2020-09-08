#  Import the Surface and read_axis files directly to the focusadd namespace
#  from their files:
from .surface.Surface import Surface
from .surface.readAxis import read_axis
from .surface.Axis import Axis


#  Imoprt the functions specified in the coils folder, which contains its own
#  __init__.py (and add the functions to focusadd namespace)
from .coils import *

# can be called using focusadd.Surface, focusadd.CoilSet() etc.



