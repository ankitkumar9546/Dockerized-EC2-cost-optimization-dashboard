import streamlit as st
import boto3
from datetime import datetime, timedelta

# -----------------------------------
# PAGE CONFIG
# -----------------------------------

st.set_page_config(
    page_title="Cloud Cost Optimizer",
    layout="wide"
)

st.title("☁ Cloud Cost Optimizer Dashboard")

# -----------------------------------
# AWS CLIENTS
# -----------------------------------

ec2 = boto3.client(
    "ec2",
    region_name="us-west-1"
)

cloudwatch = boto3.client(
    "cloudwatch",
    region_name="us-west-1"
)
# -----------------------------------
# ESTIMATED MONTHLY INSTANCE COSTS
# -----------------------------------

INSTANCE_PRICES = {
    "t2.micro": 8.5,
    "t2.small": 17,
    "t3.micro": 7.5,
    "t3.small": 15,
    "t3.medium": 30
}

# -----------------------------------
# FETCH INSTANCE DATA
# -----------------------------------

def get_instances():

    report = []

    response = ec2.describe_instances()

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:

            instance_id = instance["InstanceId"]
            state = instance["State"]["Name"]

            instance_type = instance["InstanceType"]

            monthly_cost = INSTANCE_PRICES.get(
                instance_type,
                0
            )

            avg_cpu = 0
            status = "UNKNOWN"
            recommendation = "NO DATA"
            waste_level = "LOW"

            # -----------------------------------
            # RUNNING INSTANCE METRICS
            # -----------------------------------

            if state == "running":

                metrics = cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName='CPUUtilization',
                    Dimensions=[
                        {
                            'Name': 'InstanceId',
                            'Value': instance_id
                        }
                    ],
                    StartTime=datetime.utcnow() - timedelta(hours=1),
                    EndTime=datetime.utcnow(),
                    Period=300,
                    Statistics=['Average']
                )

                datapoints = metrics['Datapoints']

                if datapoints:

                    total_cpu = sum(
                        point['Average']
                        for point in datapoints
                    )

                    avg_cpu = total_cpu / len(datapoints)

                    if avg_cpu < 5:

                        status = "IDLE"
                        recommendation = (
                            f"STOP or DOWNSIZE "
                            f"(~${monthly_cost}/month waste)"
                        )

                    elif avg_cpu < 20:

                        status = "LOW_USAGE"
                        recommendation = (
                            "MONITOR UTILIZATION"
                        )

                    else:

                        status = "ACTIVE"
                        recommendation = "HEALTHY"

                else:

                    status = "NO METRICS"
                    recommendation = "WAIT FOR DATA"

            elif state == "stopped":

                status = "STOPPED"
                recommendation = "INSTANCE OFF"

            elif state == "terminated":

                status = "TERMINATED"
                recommendation = "REMOVED"

            # -----------------------------------
            # WASTE SEVERITY
            # -----------------------------------

            if status == "IDLE" and monthly_cost >= 15:

                waste_level = "HIGH"

            elif status == "IDLE":

                waste_level = "MEDIUM"

            elif status == "LOW_USAGE":

                waste_level = "LOW"

            # -----------------------------------
            # SAVE REPORT
            # -----------------------------------

            report.append({
                "id": instance_id,
                "type": instance_type,
                "state": state,
                "cpu": round(avg_cpu, 2),
                "monthly_cost": monthly_cost,
                "waste_level": waste_level,
                "status": status,
                "recommendation": recommendation
            })

    return report

# -----------------------------------
# MASTER REFRESH BUTTON
# -----------------------------------

if st.button("🔄 Refresh All Infrastructure"):
    st.session_state.instances = get_instances()

# Initial Load

if "instances" not in st.session_state:
    st.session_state.instances = get_instances()

instances = st.session_state.instances

# -----------------------------------
# DASHBOARD METRICS
# -----------------------------------

total = len(instances)

running_count = len([
    i for i in instances
    if i["state"] == "running"
])

stopped_count = len([
    i for i in instances
    if i["state"] == "stopped"
])

terminated_count = len([
    i for i in instances
    if i["state"] == "terminated"
])

total_monthly_cost = sum(
    i["monthly_cost"]
    for i in instances
    if i["state"] == "running"
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total", total)
col2.metric("Running", running_count)
col3.metric("Stopped", stopped_count)
col4.metric(
    "Monthly Cost",
    f"${round(total_monthly_cost, 2)}"
)

st.divider()

# -----------------------------------
# GROUP INSTANCES
# -----------------------------------

running_instances = [
    i for i in instances
    if i["state"] == "running"
]

stopped_instances = [
    i for i in instances
    if i["state"] == "stopped"
]

terminated_instances = [
    i for i in instances
    if i["state"] == "terminated"
]

# -----------------------------------
# INSTANCE CARD
# -----------------------------------

def render_instance(instance):

    with st.container(border=True):

        st.subheader(f"🖥 {instance['id']}")

        st.write(f"State: **{instance['state']}**")
        st.write(f"Instance Type: **{instance['type']}**")

        # -----------------------------------
        # CPU USAGE
        # -----------------------------------

        st.write(f"CPU Usage: **{instance['cpu']}%**")

        st.progress(
            min(instance["cpu"] / 100, 1.0)
        )

        # -----------------------------------
        # COST INFO
        # -----------------------------------

        st.write(
            f"Estimated Monthly Cost: "
            f"**${instance['monthly_cost']}**"
        )

        # -----------------------------------
        # VISUAL WASTE SEVERITY
        # -----------------------------------

        if instance["waste_level"] == "HIGH":

            st.error("🔴 HIGH WASTE")

        elif instance["waste_level"] == "MEDIUM":

            st.warning("🟡 MEDIUM WASTE")

        else:

            st.success("🟢 LOW WASTE")

        # -----------------------------------
        # STATUS & RECOMMENDATION
        # -----------------------------------

        st.write(f"Status: **{instance['status']}**")

        st.write(
            f"Recommendation: "
            f"**{instance['recommendation']}**"
        )

        # -----------------------------------
        # CPU TREND GRAPH
        # -----------------------------------

        if instance["state"] == "running":

            with st.expander("📊 Show CPU Trend"):

                metrics = cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName='CPUUtilization',
                    Dimensions=[
                        {
                            'Name': 'InstanceId',
                            'Value': instance['id']
                        }
                    ],
                    StartTime=datetime.utcnow() - timedelta(hours=1),
                    EndTime=datetime.utcnow(),
                    Period=300,
                    Statistics=['Average']
                )

                datapoints = sorted(
                    metrics['Datapoints'],
                    key=lambda x: x['Timestamp']
                )

                if datapoints:

                    chart_data = {
                        "Time": [
                            point['Timestamp']
                            for point in datapoints
                        ],
                        "CPU Usage": [
                            point['Average']
                            for point in datapoints
                        ]
                    }

                    st.line_chart(
                        data=chart_data,
                        x="Time",
                        y="CPU Usage"
                    )

                else:

                    st.info(
                        "No CPU trend data available."
                    )

        # -----------------------------------
        # ACTION BUTTONS
        # -----------------------------------

        col1, col2, col3, col4 = st.columns(4)

        # REFRESH BUTTON

        if col1.button(
            "🔄 Refresh",
            key=f"refresh_{instance['id']}"
        ):

            st.session_state.instances = get_instances()
            st.rerun()

        # -----------------------------------
        # RUNNING INSTANCE ACTIONS
        # -----------------------------------

        if instance["state"] == "running":

            if col2.button(
                "⏹ Stop",
                key=f"stop_{instance['id']}"
            ):

                ec2.stop_instances(
                    InstanceIds=[instance['id']]
                )

                st.warning(
                    f"{instance['id']} stopping..."
                )

                st.session_state.instances = get_instances()
                st.rerun()

            # SAFE TERMINATE

            confirm_text = col4.text_input(
                "Type TERMINATE",
                key=f"confirm_running_{instance['id']}"
            )

            if col4.button(
                "❌ Confirm Terminate",
                key=f"terminate_running_{instance['id']}"
            ):

                if confirm_text == "TERMINATE":

                    ec2.terminate_instances(
                        InstanceIds=[instance['id']]
                    )

                    st.error(
                        f"{instance['id']} terminating..."
                    )

                    st.session_state.instances = get_instances()
                    st.rerun()

                else:

                    st.warning(
                        "⚠ Type TERMINATE exactly "
                        "to confirm deletion."
                    )

        # -----------------------------------
        # STOPPED INSTANCE ACTIONS
        # -----------------------------------

        elif instance["state"] == "stopped":

            if col2.button(
                "▶ Start",
                key=f"start_{instance['id']}"
            ):

                ec2.start_instances(
                    InstanceIds=[instance['id']]
                )

                st.success(
                    f"{instance['id']} starting..."
                )

                st.session_state.instances = get_instances()
                st.rerun()

            # SAFE TERMINATE

            confirm_text = col4.text_input(
                "Type TERMINATE",
                key=f"confirm_stopped_{instance['id']}"
            )

            if col4.button(
                "❌ Confirm Terminate",
                key=f"terminate_stopped_{instance['id']}"
            ):

                if confirm_text == "TERMINATE":

                    ec2.terminate_instances(
                        InstanceIds=[instance['id']]
                    )

                    st.error(
                        f"{instance['id']} terminating..."
                    )

                    st.session_state.instances = get_instances()
                    st.rerun()

                else:

                    st.warning(
                        "⚠ Type TERMINATE exactly "
                        "to confirm deletion."
                    )

        # -----------------------------------
        # TERMINATED INSTANCE
        # -----------------------------------

        elif instance["state"] == "terminated":

            st.info(
                "Instance terminated. "
                "No actions available."
            )

# -----------------------------------
# RUNNING INSTANCES
# -----------------------------------

with st.expander(
    f"🟢 Running Instances ({len(running_instances)})",
    expanded=True
):

    if running_instances:

        for instance in running_instances:
            render_instance(instance)

    else:

        st.write("No running instances.")

# -----------------------------------
# STOPPED INSTANCES
# -----------------------------------

with st.expander(
    f"🟡 Stopped Instances ({len(stopped_instances)})"
):

    if stopped_instances:

        for instance in stopped_instances:
            render_instance(instance)

    else:

        st.write("No stopped instances.")

# -----------------------------------
# TERMINATED INSTANCES
# -----------------------------------

with st.expander(
    f"🔴 Terminated Instances ({len(terminated_instances)})"
):

    if terminated_instances:

        for instance in terminated_instances:
            render_instance(instance)

    else:

        st.write("No terminated instances.")