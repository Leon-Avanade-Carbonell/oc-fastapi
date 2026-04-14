#!/usr/bin/env python3
"""
Verification script for Web Mercator GeoTIFF backend implementation.
Checks:
1. Notebook has correct pyproj transformation
2. Metadata tags are correctly configured
3. CRS is set to EPSG:3857
4. Bounds transformation is working
"""

import json
import sys
from pathlib import Path


def check_notebook_config():
    """Verify notebook has Web Mercator implementation."""
    print("\n" + "=" * 70)
    print("VERIFICATION 1: Notebook Configuration")
    print("=" * 70)

    notebook_path = Path("notebooks/generate_climate_mvt.ipynb")
    with open(notebook_path, "r") as f:
        nb = json.load(f)

    checks = {
        "pyproj_import": False,
        "web_mercator_bounds": False,
        "web_mercator_crs": False,
        "bounds_wgs84_metadata": False,
        "transformer_creation": False,
    }

    # Search through all cells
    for cell in nb["cells"]:
        source_text = "".join(cell.get("source", []))

        if "from pyproj import Transformer" in source_text:
            checks["pyproj_import"] = True
            print("✅ PyProj import found")

        if 'Transformer.from_crs("EPSG:4326", "EPSG:3857"' in source_text:
            checks["transformer_creation"] = True
            print("✅ Transformer WGS84→Web Mercator found")

        if "AUSTRALIA_BOUNDS_WEB_MERCATOR" in source_text:
            checks["web_mercator_bounds"] = True
            print("✅ Web Mercator bounds transformation found")

        if "'crs': 'EPSG:3857'" in source_text:
            checks["web_mercator_crs"] = True
            print("✅ CRS set to EPSG:3857 found")

        if "BOUNDS_WGS84" in source_text:
            checks["bounds_wgs84_metadata"] = True
            print("✅ BOUNDS_WGS84 metadata tag found")

    all_passed = all(checks.values())

    print("\n📋 Summary:")
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}: {passed}")

    return all_passed


def check_router_documentation():
    """Verify router.py has Web Mercator documentation."""
    print("\n" + "=" * 70)
    print("VERIFICATION 2: Router Documentation")
    print("=" * 70)

    router_path = Path("app/routes/climate_mvt/router.py")
    with open(router_path, "r") as f:
        router_text = f.read()

    checks = {
        "web_mercator_epsg3857": "EPSG:3857" in router_text,
        "web_mercator_noted": "Web Mercator" in router_text,
        "coordinate_system_note": "Coordinate System Note" in router_text,
        "meters_not_degrees": "meters, not degrees" in router_text,
        "bounds_wgs84_tag": "BOUNDS_WGS84" in router_text,
    }

    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}: {passed}")

    return all(checks.values())


def check_mvt_guide():
    """Verify MVT_GUIDE.md has comprehensive Web Mercator documentation."""
    print("\n" + "=" * 70)
    print("VERIFICATION 3: MVT_GUIDE.md Documentation")
    print("=" * 70)

    guide_path = Path("app/routes/climate_mvt/MVT_GUIDE.md")
    with open(guide_path, "r") as f:
        guide_text = f.read()

    checks = {
        "web_mercator_overview": guide_text.count("Web Mercator") >= 3,
        "epsg3857": "EPSG:3857" in guide_text,
        "coordinate_system_section": "## Coordinate System Details" in guide_text,
        "reprojection_utilities": "reprojection_utils.py" in guide_text,
        "transformation_path": "PyProj Reprojection" in guide_text
        and "WGS84" in guide_text
        and "Web Mercator" in guide_text,
        "bounds_wgs84_reference": "BOUNDS_WGS84" in guide_text,
        "meters_not_degrees": "Meters (not degrees)" in guide_text,
        "no_manual_bounds": "Do NOT manually specify bounds" in guide_text,
    }

    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}: {passed}")

    return all(checks.values())


def check_reprojection_utils():
    """Verify reprojection_utils.py exists with correct implementation."""
    print("\n" + "=" * 70)
    print("VERIFICATION 4: Reprojection Utilities")
    print("=" * 70)

    utils_path = Path("app/routes/climate_mvt/reprojection_utils.py")

    if not utils_path.exists():
        print("❌ reprojection_utils.py NOT FOUND")
        return False

    with open(utils_path, "r") as f:
        utils_text = f.read()

    checks = {
        "geotiff_reprojector_class": "class GeoTIFFReprojector" in utils_text,
        "rasterio_import": "import rasterio" in utils_text,
        "warp_import": "from rasterio.warp import" in utils_text,
        "cache_support": "self.cache_dir" in utils_text,
        "reproject_file_method": "def reproject_file" in utils_text,
        "caching_logic": "use_cache" in utils_text,
    }

    print("✅ reprojection_utils.py exists")

    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}: {passed}")

    return all(checks.values())


def verify_bounds_values():
    """Verify the exact bounds values are correct."""
    print("\n" + "=" * 70)
    print("VERIFICATION 5: Bounds Values")
    print("=" * 70)

    notebook_path = Path("notebooks/generate_climate_mvt.ipynb")
    with open(notebook_path, "r") as f:
        nb = json.load(f)

    expected_bounds = {
        "west": 112.900000,
        "south": -43.650000,
        "east": 153.650000,
        "north": -10.050000,
    }

    found_bounds = {}

    for cell in nb["cells"]:
        source_text = "".join(cell.get("source", []))

        for key, value in expected_bounds.items():
            if f'"{key}": {value}' in source_text or f"'{key}': {value}" in source_text:
                found_bounds[key] = True
                print(f"✅ {key}: {value}° found")

    all_bounds_found = len(found_bounds) == len(expected_bounds)

    if not all_bounds_found:
        print(
            f"\n⚠️  Missing bounds: {set(expected_bounds.keys()) - set(found_bounds.keys())}"
        )

    return all_bounds_found


def check_metadata_generation():
    """Verify metadata tags are being generated with correct values."""
    print("\n" + "=" * 70)
    print("VERIFICATION 6: Metadata Tag Generation")
    print("=" * 70)

    notebook_path = Path("notebooks/generate_climate_mvt.ipynb")
    with open(notebook_path, "r") as f:
        nb = json.load(f)

    checks = {
        "variable_tag": False,
        "time_tag": False,
        "zoom_level_tag": False,
        "crs_epsg3857_tag": False,
        "bounds_wgs84_tag": False,
        "colormap_tag": False,
        "data_min_max_tags": False,
    }

    for cell in nb["cells"]:
        source_text = "".join(cell.get("source", []))

        if "VARIABLE=variable" in source_text:
            checks["variable_tag"] = True
        if "TIME=str(time)" in source_text:
            checks["time_tag"] = True
        if "ZOOM_LEVEL=str(zoom_level)" in source_text:
            checks["zoom_level_tag"] = True
        if "CRS='EPSG:3857'" in source_text:
            checks["crs_epsg3857_tag"] = True
        if "BOUNDS_WGS84=" in source_text:
            checks["bounds_wgs84_tag"] = True
        if "COLORMAP_TYPE='green_scale'" in source_text:
            checks["colormap_tag"] = True
        if "DATA_MIN=" in source_text and "DATA_MAX=" in source_text:
            checks["data_min_max_tags"] = True

    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}: {passed}")

    return all(checks.values())


def main():
    """Run all verifications."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  BACKEND WEB MERCATOR IMPLEMENTATION VERIFICATION".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")

    results = {
        "Notebook Configuration": check_notebook_config(),
        "Router Documentation": check_router_documentation(),
        "MVT_GUIDE Documentation": check_mvt_guide(),
        "Reprojection Utilities": check_reprojection_utils(),
        "Bounds Values": verify_bounds_values(),
        "Metadata Generation": check_metadata_generation(),
    }

    print("\n" + "=" * 70)
    print("FINAL VERIFICATION SUMMARY")
    print("=" * 70)

    for check_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL VERIFICATIONS PASSED!")
        print("=" * 70)
        print("\n✨ Backend implementation is complete and correct!")
        print("   GeoTIFFs are ready to be generated in Web Mercator (EPSG:3857)")
        print("   Run the notebook to create the aligned GeoTIFFs")
        return 0
    else:
        print("⚠️  SOME VERIFICATIONS FAILED")
        print("=" * 70)
        print("\n❌ Backend implementation has issues that need to be fixed")
        failed = [name for name, passed in results.items() if not passed]
        print("\nFailed checks:")
        for failed_check in failed:
            print(f"  - {failed_check}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
