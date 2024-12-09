# app.py
from datetime import date, timedelta, datetime
import streamlit as st
from auth_helpers import login, logout, handle_callback, get_user
from aws_helpers import fetch_ec2_data, fetch_s3_data, fetch_cost_data, fetch_iam_users
from dotenv import load_dotenv

load_dotenv()

# Set page configuration
st.set_page_config(page_title="AWS Authority", layout="wide")

# Clear session state at app startup
if "clear_session" not in st.session_state:
    st.session_state.clear()
    st.session_state["clear_session"] = True

# Handle Auth0 callback
if "user" not in st.session_state:
    user_info = handle_callback()
    if user_info:
        st.session_state["user"] = user_info

# Authentication check
user = get_user()
if not user:
    st.title("Welcome to AWS Authority!")
    st.warning("Please log in to access this application.")
    login()
    st.stop()

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.write(f"Signed in as: {user.get('email', 'Unknown')}")
if st.sidebar.button("Logout"):
    logout()

selection = st.sidebar.radio("Go to", ["Dashboard", "Profile"])

# Profile page
if selection == "Profile":
    st.title("User Profile")
    st.write("Authenticated as:", user.get("name", "Unknown"))
    st.write("Email:", user.get("email", "Unknown"))

    st.write("Provide your AWS keys and region to start fetching data:")
    with st.form("profile_form"):
        access_key = st.text_input("Access Key", type="password")
        secret_key = st.text_input("Secret Key", type="password")
        region = st.selectbox("AWS Region", ["us-east-1", "us-east-2", "us-west-1", "us-west-2"])
        submitted = st.form_submit_button("Save")

    if submitted:
        st.success("AWS credentials saved!")
        st.session_state["aws_keys"] = {
            "access_key": access_key,
            "secret_key": secret_key,
            "region": region,
        }

# Dashboard page
elif selection == "Dashboard":
    st.title("AWS Authority Dashboard")

    # Validate AWS credentials
    if "aws_keys" not in st.session_state:
        st.error("Please complete your profile to fetch AWS data.")
        st.stop()

    aws_keys = st.session_state["aws_keys"]

    # Fetch data with user-selected date range
    today = date.today()
    default_start = today - timedelta(days=30)

    st.sidebar.header("Cost Data Date Range")
    start_date = st.sidebar.date_input("Start Date", default_start, key="start_date")
    end_date = st.sidebar.date_input("End Date", today, key="end_date")

    if start_date > end_date:
        st.error("Start date cannot be after end date.")
        st.stop()

    # Refresh button and timestamp
    if st.button("Refresh Data"):
        st.session_state["last_refreshed"] = datetime.now()

    # Check or update last refreshed timestamp
    last_refreshed = st.session_state.get("last_refreshed")
    if not last_refreshed:
        st.session_state["last_refreshed"] = datetime.now()

    st.info(f"Last Refreshed: {st.session_state['last_refreshed'].strftime('%Y-%m-%d %I:%M:%S %p')}")

    # Fetch AWS data
    ec2_data = fetch_ec2_data(aws_keys)
    s3_data = fetch_s3_data(aws_keys)
    cost_data = fetch_cost_data(aws_keys, start_date=start_date, end_date=end_date)
    iam_data = fetch_iam_users(aws_keys)

    # EC2 Visualization
    st.subheader("EC2 Instances")
    if ec2_data.get("chart"):
        st.plotly_chart(ec2_data["chart"], use_container_width=True, key="ec2_chart")
    else:
        st.warning("No EC2 instances found.")

    # S3 Visualization
    st.subheader("S3 Buckets")
    if s3_data.get("chart"):
        st.plotly_chart(s3_data["chart"], use_container_width=True, key="s3_chart")
    else:
        st.warning("No S3 buckets found.")

    # Cost Analysis Visualization
    st.subheader("Cost Analysis")
    if cost_data.get("service_chart"):
        st.plotly_chart(cost_data["service_chart"], use_container_width=True, key="cost_service_chart")
    else:
        st.warning("Service cost chart is unavailable.")

    if cost_data.get("summary_chart"):
        st.plotly_chart(cost_data["summary_chart"], use_container_width=True, key="cost_summary_chart")
    else:
        st.warning("Summary cost chart is unavailable.")

    # IAM Users Table
    st.subheader("IAM Users and Policies")
    if not iam_data:
        st.warning("No IAM users found.")
    else:
        for i, user in enumerate(iam_data, start=1):
            st.write(f"**{i}. User:** {user['user_name']}")
            st.markdown("**Attached Policies:**")
            with st.container():
                for j, policy in enumerate(user["policies"], start=1):
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{j}. {policy}", unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
