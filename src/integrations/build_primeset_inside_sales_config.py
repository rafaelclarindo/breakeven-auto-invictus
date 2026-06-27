#!/usr/bin/env python3
"""Wrapper Primeset → build_growthpack_inside_sales_config (perfil primeset)."""
from build_growthpack_inside_sales_config import main

if __name__ == "__main__":
    import sys

    if "--profile" not in sys.argv:
        sys.argv.extend(["--profile", "primeset"])
    main()
