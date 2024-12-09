import boto3
from botocore.exceptions import ClientError
import plotly.graph_objects as go
import random

def fetch_iam_users(aws_keys):
    session = boto3.Session(
        aws_access_key_id=aws_keys["access_key"],
        aws_secret_access_key=aws_keys["secret_key"],
        region_name=aws_keys["region"]
    )
    iam_client = session.client("iam")
    users = []

    try:
        response = iam_client.list_users()
        for user in response["Users"]:
            user_name = user["UserName"]

            # Fetch attached policies
            attached_policies_response = iam_client.list_attached_user_policies(UserName=user_name)
            attached_policies = [policy["PolicyName"] for policy in attached_policies_response.get("AttachedPolicies", [])]

            # Fetch inline policies
            inline_policies_response = iam_client.list_user_policies(UserName=user_name)
            inline_policies = inline_policies_response.get("PolicyNames", [])

            # Combine all policies
            all_policies = attached_policies + inline_policies

            users.append({
                "user_name": user_name,
                "policies": all_policies
            })
    except ClientError as e:
        print(f"ClientError fetching IAM users: {e}")
    except Exception as e:
        print(f"Error fetching IAM users: {e}")

    return users


def fetch_ec2_data(aws_keys):
    session = boto3.Session(
        aws_access_key_id=aws_keys["access_key"],
        aws_secret_access_key=aws_keys["secret_key"],
        region_name=aws_keys["region"]
    )
    ec2 = session.resource("ec2")
    instances = list(ec2.instances.all())

    total = len(instances)
    active = sum(1 for instance in instances if instance.state["Name"] == "running")

    ec2_colors = ["#FF9900", "#FFCC80"]  # AWS EC2 orange shades

    if total == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No Data Available",
            showarrow=False,
            font_size=20
        )
    else:
        fig = go.Figure(data=[
            go.Pie(
                labels=["Active", "Inactive"],
                values=[active, total - active],
                marker=dict(colors=ec2_colors)
            )
        ])
        fig.update_layout(title="EC2 Instances Overview")

    return {"chart": fig}


def fetch_s3_data(aws_keys):
    session = boto3.Session(
        aws_access_key_id=aws_keys["access_key"],
        aws_secret_access_key=aws_keys["secret_key"],
        region_name=aws_keys["region"]
    )
    s3 = session.resource("s3")
    buckets = list(s3.buckets.all())

    total = len(buckets)
    active = sum(1 for bucket in buckets if list(bucket.objects.limit(1)))

    s3_colors = ["#1D8102", "#A6DF8C"]  # AWS S3 green shades

    if total == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No Data Available",
            showarrow=False,
            font_size=20
        )
    else:
        fig = go.Figure(data=[
            go.Pie(
                labels=["In-Use", "Empty"],
                values=[active, total - active],
                marker=dict(colors=s3_colors)
            )
        ])
        fig.update_layout(title="S3 Buckets Overview")

    return {"chart": fig}


def fetch_cost_data(aws_keys, start_date, end_date):
    client = boto3.client(
        "ce",
        aws_access_key_id=aws_keys["access_key"],
        aws_secret_access_key=aws_keys["secret_key"],
        region_name=aws_keys["region"]
    )

    try:
        total_cost = client.get_cost_and_usage(
            TimePeriod={"Start": start_date.isoformat(), "End": end_date.isoformat()},
            Granularity="MONTHLY",
            Metrics=["UNBLENDED_COST"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]
        )

        services = []
        costs = []
        colors = []

        for group in total_cost.get("ResultsByTime", []):
            for group_item in group.get("Groups", []):
                service = group_item.get("Keys", [])[0]
                amount = group_item.get("Metrics", {}).get("UnblendedCost", {}).get("Amount", 0)
                if service and amount:
                    services.append(service)
                    costs.append(float(amount))
                    colors.append(f"#{random.randint(0, 0xFFFFFF):06x}")  # Generate random colors

        total_amount = sum(costs)
        avg_monthly = total_amount / 12 if total_amount > 0 else 0

        fig = go.Figure(data=[
            go.Bar(name="Service Costs", x=services, y=costs, marker=dict(color=colors))
        ])
        fig.update_layout(
            title="Cost Analysis by Service",
            xaxis_title="AWS Services",
            yaxis_title="Cost (USD)",
            barmode="stack"
        )

        summary_fig = go.Figure(data=[
            go.Bar(name="Total Cost", x=["Total"], y=[total_amount]),
            go.Bar(name="Avg Monthly Cost", x=["Average"], y=[avg_monthly])
        ])
        summary_fig.update_layout(
            title="Total and Average Monthly Costs",
            xaxis_title="Category",
            yaxis_title="Cost (USD)",
            barmode="group"
        )

        return {"service_chart": fig, "summary_chart": summary_fig}
    except ClientError as e:
        print(f"ClientError during cost data fetch: {e}")
    except Exception as e:
        print(f"Error during cost data fetch: {e}")

    fallback_fig = go.Figure()
    fallback_fig.add_annotation(text="Cost Data Unavailable", showarrow=False, font_size=20)
    return {"service_chart": fallback_fig, "summary_chart": fallback_fig}
