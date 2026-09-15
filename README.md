# OCI Service Limit Tool

Exports all OCI tenancy service limits for a requested region to CSV. It works in OCI Cloud Shell or on a local macOS/Linux terminal with an authenticated OCI configuration.

## Prerequisites

- Python 3.9 or newer
- OCI Python SDK
- An authenticated OCI profile with permission to inspect service limits and
  resource availability

Install the SDK locally if needed:

```bash
python3 -m venv path/to/venv
source path/to/venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Run

```bash
python3 export_service_limits.py \
  '<tenancy-ocid>' \
  '<region-name>' \
  --config-file <config-file-path> \
  --output <region-name>_service_limits.csv

Example:

python3 export_service_limits.py \
  'ocid1.tenancy.oc1..aaaaaaaa' \
  'us-phoenix-1' \
  --config-file /.oci/config \
  --output phoenix_service_limits.csv
```



## Output

The main CSV has these columns:

```text
region,service_name,service_description,limit_name,scope_type,availability_domain,current_limit,usage,available
```

OCI does not support usage and availability for every limit. Such rows remain in the main CSV with blank `usage` and `available` fields; their details are recorded in a companion `*_warnings.csv` file.
