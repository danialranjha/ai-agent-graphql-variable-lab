def get_export_status(config: Dict[str, str], export_id: str) -> Dict[str, Any]:
    """Query the status of a vulnerability export job.

    Sends a GraphQL query to retrieve the current status of an export job,
    including its completion state and available Parquet file URLs.

    Args:
        config: Configuration dictionary containing endpoint and api_key.
        export_id: The export ID to query status for

    Returns:
        dict: Export status information containing:
            - id (str): The export ID
            - status (str): Current status (PENDING, PROCESSING, COMPLETE, FAILED)
            - parquetFiles (list[str]): Flat list of Parquet file URLs
            - result (list[dict]): List of {prefix, urls} objects from the API response

    Raises:
        requests.HTTPError: If the HTTP response status code is not 200
        ValueError: If the response contains GraphQL errors
        requests.RequestException: If the network request fails
    """
    query = (
        """
    {
      export(id: "%s") {
        id
        status
        dataset
        timestamp
        result {
          prefix
          urls
        }
      }
    }
    """
        % export_id
    )

    response = send_graphql_request(endpoint=config["endpoint"], api_key=config["api_key"], query=query)
    export_data = response["data"]["export"]

    parquet_urls = []
    result_list = export_data.get("result") or []
    for item in result_list:
        if isinstance(item, dict) and "urls" in item:
            parquet_urls.extend(item["urls"])

    return {
        "id": export_data["id"],
        "status": export_data["status"],
        "parquetFiles": parquet_urls,
        "result": result_list,
    }
