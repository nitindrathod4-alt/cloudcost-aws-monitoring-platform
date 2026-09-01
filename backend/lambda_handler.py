import json
import os
from datetime import date, datetime, timedelta

import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION_NAME", os.environ.get("AWS_DEFAULT_REGION", "ap-south-1"))
CE_REGION = "us-east-1"
SNAPSHOT_TABLE = os.environ.get("SNAPSHOT_TABLE")
ALERT_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN")


def client(name, region=None):
    return boto3.client(name, region_name=region or REGION)


def response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": os.environ.get("CORS_ORIGIN", "*"),
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        },
        "body": json.dumps(body, default=str),
    }


def safe(callable_, default):
    try:
        return callable_()
    except Exception as exc:
        print(f"AWS read failed: {type(exc).__name__}: {exc}")
        return default


def month_bounds(offset=0):
    today = date.today()
    first = today.replace(day=1)
    for _ in range(offset):
        first = (first - timedelta(days=1)).replace(day=1)
    if offset == 0:
        end = today + timedelta(days=1)
    else:
        end = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first.isoformat(), end.isoformat()


def cost_usage(start, end, granularity="DAILY", group_by=None):
    ce = client("ce", CE_REGION)
    kwargs = {"TimePeriod": {"Start": start, "End": end}, "Granularity": granularity, "Metrics": ["UnblendedCost"]}
    if group_by:
        kwargs["GroupBy"] = [{"Type": "DIMENSION", "Key": group_by}]
    return safe(lambda: ce.get_cost_and_usage(**kwargs), {"ResultsByTime": []})


def amount(metric):
    return float(metric.get("Amount", 0) or 0)


def dashboard_data():
    start, end = month_bounds(0)
    prev_start, prev_end = month_bounds(1)
    daily = cost_usage(start, end, "DAILY")
    services = cost_usage(start, end, "MONTHLY", "SERVICE")
    previous = cost_usage(prev_start, prev_end, "MONTHLY")
    total = sum(amount(r.get("Total", {}).get("UnblendedCost", {})) for r in daily.get("ResultsByTime", []))
    previous_total = sum(amount(r.get("Total", {}).get("UnblendedCost", {})) for r in previous.get("ResultsByTime", []))

    service_rows = []
    if services.get("ResultsByTime"):
        for group in services["ResultsByTime"][0].get("Groups", []):
            value = amount(group.get("Metrics", {}).get("UnblendedCost", {}))
            service_rows.append({"service": group.get("Keys", ["Unknown"])[0], "cost": value})
    service_rows.sort(key=lambda x: x["cost"], reverse=True)

    forecast = safe(lambda: client("ce", CE_REGION).get_cost_forecast(
        TimePeriod={"Start": end, "End": (date.today() + timedelta(days=31)).isoformat()},
        Metric="UNBLENDED_COST", Granularity="MONTHLY"), {"Total": {"Amount": str(total)}})
    forecast_value = amount(forecast.get("Total", {}))

    budget_data = safe(lambda: client("budgets", REGION).describe_budgets(AccountId=_account_id()), {"Budgets": []})
    budgets = []
    for b in budget_data.get("Budgets", []):
        budgets.append({"name": b.get("BudgetName"), "limit": float(b.get("BudgetLimit", {}).get("Amount", 0) or 0), "type": b.get("BudgetType")})
    budget = budgets[0] if budgets else {"name": "No AWS Budget", "limit": 0, "type": "COST"}

    return {
        "period": {"start": start, "end": end},
        "total_cost": total,
        "previous_month_cost": previous_total,
        "month_change_percent": ((total - previous_total) / previous_total * 100) if previous_total else 0,
        "forecast_cost": forecast_value,
        "budget": budget,
        "budget_used_percent": (total / budget["limit"] * 100) if budget["limit"] else 0,
        "daily": [{"date": r.get("TimePeriod", {}).get("Start"), "cost": amount(r.get("Total", {}).get("UnblendedCost", {}))} for r in daily.get("ResultsByTime", [])],
        "services": service_rows[:12],
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }


def _account_id():
    return client("sts").get_caller_identity()["Account"]


def resources_data():
    ec2 = safe(lambda: client("ec2").describe_instances(), {"Reservations": []})
    instances = []
    for reservation in ec2.get("Reservations", []):
        for item in reservation.get("Instances", []):
            name = next((t.get("Value") for t in item.get("Tags", []) if t.get("Key") == "Name"), item.get("InstanceId"))
            instances.append({"name": name, "id": item.get("InstanceId"), "type": "EC2", "region": REGION, "status": item.get("State", {}).get("Name")})

    rds = safe(lambda: client("rds").describe_db_instances(), {"DBInstances": []})
    databases = [{"name": d.get("DBInstanceIdentifier"), "id": d.get("DbiResourceId"), "type": "RDS", "region": REGION, "status": d.get("DBInstanceStatus")} for d in rds.get("DBInstances", [])]

    buckets = safe(lambda: client("s3", "us-east-1").list_buckets(), {"Buckets": []})
    s3 = [{"name": b.get("Name"), "id": b.get("Name"), "type": "S3", "region": "Global", "status": "Active"} for b in buckets.get("Buckets", [])]

    functions = safe(lambda: client("lambda").list_functions(), {"Functions": []})
    lambdas = [{"name": f.get("FunctionName"), "id": f.get("FunctionArn"), "type": "Lambda", "region": REGION, "status": "Active"} for f in functions.get("Functions", [])]

    distributions = safe(lambda: client("cloudfront", "us-east-1").list_distributions(), {"DistributionList": {"Items": []}})
    cloudfront = [{"name": d.get("DomainName"), "id": d.get("Id"), "type": "CloudFront", "region": "Global", "status": d.get("Status")} for d in distributions.get("DistributionList", {}).get("Items", [])]
    return instances + databases + s3 + lambdas + cloudfront


def monitoring_data():
    cw = client("cloudwatch")
    end = datetime.utcnow()
    start = end - timedelta(hours=3)

    def latest(namespace, name):
        result = safe(lambda: cw.get_metric_statistics(Namespace=namespace, MetricName=name, StartTime=start, EndTime=end, Period=300, Statistics=["Average"]), {"Datapoints": []})
        points = sorted(result.get("Datapoints", []), key=lambda x: x.get("Timestamp", datetime.min))
        return points[-1].get("Average", 0) if points else 0

    return {"ec2_cpu": latest("AWS/EC2", "CPUUtilization"), "rds_cpu": latest("AWS/RDS", "CPUUtilization"), "updated_at": end.isoformat() + "Z"}


def security_data():
    trails = safe(lambda: client("cloudtrail").describe_trails(includeShadowTrails=False), {"trailList": []})
    ct = client("cloudtrail")
    trail_status = []
    for trail in trails.get("trailList", []):
        status = safe(lambda t=trail: ct.get_trail_status(Name=t["Name"]), {})
        trail_status.append({"name": trail.get("Name"), "is_logging": status.get("IsLogging", False)})
    iam_summary = safe(lambda: client("iam", "us-east-1").get_account_summary(), {"SummaryMap": {}})
    waf = safe(lambda: client("wafv2", "us-east-1").list_web_acls(Scope="CLOUDFRONT"), {"WebACLs": []})
    return {"cloudtrail": trail_status, "iam_users": iam_summary.get("SummaryMap", {}).get("Users", 0), "iam_roles": iam_summary.get("SummaryMap", {}).get("Roles", 0), "waf_acls": len(waf.get("WebACLs", []))}


def budgets_data():
    data = safe(lambda: client("budgets", REGION).describe_budgets(AccountId=_account_id()), {"Budgets": []})
    return [{"name": b.get("BudgetName"), "limit": float(b.get("BudgetLimit", {}).get("Amount", 0) or 0), "actual": float(b.get("CalculatedSpend", {}).get("ActualSpend", {}).get("Amount", 0) or 0), "forecast": float(b.get("CalculatedSpend", {}).get("ForecastedSpend", {}).get("Amount", 0) or 0), "type": b.get("BudgetType")} for b in data.get("Budgets", [])]


def save_snapshot(data):
    if not SNAPSHOT_TABLE:
        return
    safe(lambda: client("dynamodb").put_item(TableName=SNAPSHOT_TABLE, Item={
        "snapshot_type": {"S": "dashboard"},
        "updated_at": {"S": data["updated_at"]},
        "total_cost": {"N": str(data["total_cost"])},
        "forecast_cost": {"N": str(data["forecast_cost"])},
    }), {})


def publish_budget_alert(data):
    if not ALERT_TOPIC_ARN or not data.get("budget_used_percent") or data["budget_used_percent"] < 80:
        return
    safe(lambda: client("sns").publish(
        TopicArn=ALERT_TOPIC_ARN,
        Subject="CloudCost AWS Budget Alert",
        Message=f"CloudCost detected {data['budget_used_percent']:.1f}% AWS budget usage. Current cost: ${data['total_cost']:.2f}.",
    ), {})


def scheduled_refresh():
    data = dashboard_data()
    save_snapshot(data)
    publish_budget_alert(data)
    return {"status": "refreshed", "updated_at": data["updated_at"], "total_cost": data["total_cost"]}


def handler(event, context):
    if event.get("source") == "aws.events":
        try:
            return scheduled_refresh()
        except Exception as exc:
            print(f"Scheduled refresh failed: {type(exc).__name__}: {exc}")
            raise

    method = event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod", "GET"))
    if method == "OPTIONS":
        return response(204, {})
    path = event.get("rawPath") or event.get("path") or "/"
    routes = {"/api/dashboard": dashboard_data, "/api/cost": dashboard_data, "/api/resources": resources_data, "/api/monitoring": monitoring_data, "/api/security": security_data, "/api/budgets": budgets_data}
    if path in routes:
        try:
            return response(200, routes[path]())
        except Exception as exc:
            print(f"Unhandled API error: {type(exc).__name__}: {exc}")
            return response(500, {"message": "AWS API request failed", "error": str(exc)})
    return response(200, {"service": "CloudCost", "status": "ok", "region": REGION, "routes": list(routes)})
