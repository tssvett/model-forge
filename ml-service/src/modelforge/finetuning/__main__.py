"""Allow running fine-tuning CLI via: python -m modelforge.finetuning"""

import sys

from .cli import main

sys.exit(main())
