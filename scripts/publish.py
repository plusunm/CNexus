import shutil
from pathlib import Path


def create_release_package():
    version = "1.0.0-g1"
    package_name = f"brain-memory-g1-{version}"
    root = Path(__file__).resolve().parent.parent
    dist_dir = root / "dist" / package_name

    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    shutil.copytree(
        root,
        dist_dir,
        ignore=shutil.ignore_patterns(
            "memory/lancedb",
            "memory/kuzu_db",
            "__pycache__",
            "*.log",
            "dist",
            ".git",
        ),
    )

    shutil.make_archive(str(root / "dist" / package_name), "zip", dist_dir)
    print(f"Release package created: dist/{package_name}.zip")


if __name__ == "__main__":
    create_release_package()
