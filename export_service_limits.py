#!/usr/bin/env python3
"""Export OCI tenancy service limits for one region to CSV."""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import oci
from oci.exceptions import RequestException, ServiceError


CSV_COLUMNS = [
    "region",
    "service_name",
    "service_description",
    "limit_name",
    "scope_type",
    "availability_domain",
    "current_limit",
    "usage",
    "available",
]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export all OCI tenancy service limits for a region to CSV."
    )
    parser.add_argument("tenancy_ocid", help="Tenancy OCID")
    parser.add_argument("region", help="OCI region, for example us-phoenix-1")
    parser.add_argument(
        "--output",
        default=None,
        help="CSV path (default: service_limits_<region>.csv in the current directory)",
    )
    parser.add_argument("--config-file", default=None, help="OCI config file path")
    parser.add_argument("--profile", default="DEFAULT", help="OCI profile (default: DEFAULT)")
    return parser.parse_args()


def create_limits_client(config_file: str | None, profile: str, region: str) -> oci.limits.LimitsClient:
    configured_values = oci.config.from_file(file_location=config_file, profile_name=profile)
    region_config = dict(configured_values)
    region_config["region"] = region
    oci.config.validate_config(region_config)
    return oci.limits.LimitsClient(
        region_config,
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
        timeout=(30, 120),
    )


def call_with_transport_retry(operation, *args, **kwargs):
    for attempt in range(3):
        try:
            return operation(*args, **kwargs)
        except RequestException:
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))


def availability(client: oci.limits.LimitsClient, tenancy_ocid: str, service_name: str, limit_value):
    kwargs = {}
    if getattr(limit_value, "scope_type", None) == "AD":
        availability_domain = getattr(limit_value, "availability_domain", None)
        if not availability_domain:
            return "", ""
        kwargs["availability_domain"] = availability_domain

    response = call_with_transport_retry(
        client.get_resource_availability,
        service_name,
        limit_value.name,
        tenancy_ocid,
        **kwargs,
    )
    return response.data.used, response.data.available


def main() -> int:
    args = parse_arguments()
    output_path = Path(args.output or f"service_limits_{args.region}.csv").expanduser().resolve()
    warnings_path = output_path.with_name(f"{output_path.stem}_warnings.csv")

    try:
        client = create_limits_client(args.config_file, args.profile, args.region)
        services = oci.pagination.list_call_get_all_results(
            client.list_services,
            args.tenancy_ocid,
            retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
        ).data
    except (RequestException, ServiceError, OSError) as error:
        print(f"Unable to list Limits services in {args.region}: {error}", file=sys.stderr)
        return 1

    with output_path.open("w", newline="", encoding="utf-8") as output_file, warnings_path.open(
        "w", newline="", encoding="utf-8"
    ) as warnings_file:
        writer = csv.DictWriter(output_file, fieldnames=CSV_COLUMNS)
        warning_writer = csv.DictWriter(
            warnings_file,
            fieldnames=["region", "service_name", "limit_name", "operation", "error"],
        )
        writer.writeheader()
        warning_writer.writeheader()

        for service in services:
            try:
                limit_values = oci.pagination.list_call_get_all_results(
                    client.list_limit_values,
                    args.tenancy_ocid,
                    service_name=service.name,
                    retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
                ).data
            except (RequestException, ServiceError) as error:
                warning_writer.writerow(
                    {
                        "region": args.region,
                        "service_name": service.name,
                        "limit_name": "",
                        "operation": "list_limit_values",
                        "error": str(error).replace("\n", " "),
                    }
                )
                continue

            for limit_value in limit_values:
                usage = available = ""
                try:
                    usage, available = availability(client, args.tenancy_ocid, service.name, limit_value)
                except (RequestException, ServiceError) as error:
                    # OCI does not support resource availability for every limit.
                    warning_writer.writerow(
                        {
                            "region": args.region,
                            "service_name": service.name,
                            "limit_name": limit_value.name,
                            "operation": "get_resource_availability",
                            "error": str(error).replace("\n", " "),
                        }
                    )

                writer.writerow(
                    {
                        "region": args.region,
                        "service_name": service.name,
                        "service_description": getattr(service, "description", "") or "",
                        "limit_name": limit_value.name,
                        "scope_type": getattr(limit_value, "scope_type", "") or "",
                        "availability_domain": getattr(limit_value, "availability_domain", "") or "",
                        "current_limit": getattr(limit_value, "value", ""),
                        "usage": usage,
                        "available": available,
                    }
                )

    print(f"Created: {output_path}")
    print(f"Availability warnings: {warnings_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
