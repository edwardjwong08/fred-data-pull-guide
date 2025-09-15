# Makefile for FRED SEP + Actuals project

PYTHON := python
MAIN   := combine.py
OUTDIR := output_data

# Output files
SEP_TIDY := $(OUTDIR)/sep_with_actuals_tidy.csv
SEP_WIDE := $(OUTDIR)/sep_only_wide.csv

.PHONY: all run clean preview

# Default target: build everything
all: $(SEP_TIDY) $(SEP_WIDE)

# Run the main script to generate outputs
$(SEP_TIDY) $(SEP_WIDE): $(MAIN) config.py fred_utils.py sep_utils.py actuals_utils.py | $(OUTDIR)
	$(PYTHON) $(MAIN)

# Ensure output directory exists
$(OUTDIR):
	mkdir -p $(OUTDIR)

# Explicit command to run everything
run:
	$(PYTHON) $(MAIN)

# Show first 20 lines of the tidy file
preview: $(SEP_TIDY)
	head -n 20 $(SEP_TIDY)

# Clean up generated CSVs
clean:
	rm -f $(SEP_TIDY) $(SEP_WIDE)

