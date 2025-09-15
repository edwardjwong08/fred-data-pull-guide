import os
import subprocess
import sys

# === Configuration ===
PYTHON = sys.executable  # Uses current Python interpreter
MAIN = "src/combine.py"
OUTDIR = "output_data"

SEP_TIDY = os.path.join(OUTDIR, "sep_with_actuals_tidy.csv")
SEP_WIDE = os.path.join(OUTDIR, "sep_only_wide.csv")

# === Helper functions ===
def ensure_outdir():
    os.makedirs(OUTDIR, exist_ok=True)

def run_main():
    ensure_outdir()
    subprocess.run([PYTHON, MAIN], check=True)

def preview_file(file_path, lines=20):
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist. Run the script first.")
        return
    with open(file_path, "r") as f:
        for i, line in enumerate(f):
            if i >= lines:
                break
            print(line, end="")

def clean():
    for f in [SEP_TIDY, SEP_WIDE]:
        if os.path.exists(f):
            os.remove(f)
            print(f"Deleted {f}")

# === Main CLI ===
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Python build script (replaces Makefile)")
    parser.add_argument("target", nargs="?", default="all",
                        choices=["all", "run", "preview", "clean"],
                        help="Target to execute (default: all)")
    args = parser.parse_args()

    if args.target == "all":
        run_main()
    elif args.target == "run":
        run_main()
    elif args.target == "preview":
        preview_file(SEP_TIDY)
    elif args.target == "clean":
        clean()