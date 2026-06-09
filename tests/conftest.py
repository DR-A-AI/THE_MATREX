import sys
import asyncio
import pytest

# Set event loop policy at module level so it runs during collection
if sys.platform == "win32":
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
