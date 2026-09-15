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

## Run - Export Service Limit

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



## OCI Service Limit CSV Compare Tool

Compares two OCI service-limit CSV exports and creates a diff CSV containing only matching limits whose `current_limit` differs.

The script matches a limit by:

- `service_name`
- `limit_name`
- `scope_type`
- `availability_domain`

This is more precise than using `service_name` alone because each service can have many independent limits.

## Run

```bash
python3 compare_service_limit.py \
  /path/to/source_service_limits.csv \
  /path/to/target_service_limits.csv \
  --output service_limit_current_limit_diff.csv
```

The output includes each affected service and limit alongside its current limit in the source and target regions.

