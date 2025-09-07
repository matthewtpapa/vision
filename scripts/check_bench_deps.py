import os
import sys

try:
    import numpy  # noqa: F401
    import PIL  # noqa: F401  # pillow

    print("bench deps OK")
except Exception:
    if os.environ.get("CI"):
        sys.exit("✖ bench requires pillow and numpy (CI should install these earlier).")
    sys.exit("✖ bench requires 'pillow' and 'numpy'. Run: python -m pip install pillow numpy")
