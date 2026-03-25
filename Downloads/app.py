import streamlit as st
import pandas as pd
import json
import os
import altair as alt

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="Advanced Voting System",
    layout="centered",
    page_icon="🗳️"
)

DATA_FILE = "poll_data.json"
ADMIN_PASSWORD = "admin123"   # 🔐 change this for your project


# -----------------------------
# DATA HELPERS
# -----------------------------
def load_data():
    """Load poll data from a JSON file."""
    if not os.path.exists(DATA_FILE):
        return {"polls": [], "active_poll_id": None}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # If file is corrupted
        return {"polls": [], "active_poll_id": None}


def save_data(data):
    """Save poll data to a JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def get_active_poll(data):
    """Return the active poll dict or None."""
    active_id = data.get("active_poll_id")
    if active_id is None:
        return None
    for poll in data["polls"]:
        if poll["id"] == active_id:
            return poll
    return None


def get_new_poll_id(data):
    """Generate a new unique poll ID."""
    if not data["polls"]:
        return 1
    return max(p["id"] for p in data["polls"]) + 1


# -----------------------------
# SESSION STATE INITIALIZATION
# -----------------------------
if "data" not in st.session_state:
    st.session_state.data = load_data()

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "voted_polls" not in st.session_state:
    st.session_state.voted_polls = []   # store poll IDs user already voted in


# -----------------------------
# SIDEBAR NAVIGATION & LOGIN
# -----------------------------
st.sidebar.title("🧭 Navigation")
mode = st.sidebar.radio("Go to", ["User Voting", "Admin Dashboard"])

st.sidebar.markdown("---")
st.sidebar.subheader("🔐 Admin Login")

if not st.session_state.is_admin:
    password_input = st.sidebar.text_input("Enter admin password", type="password")
    if st.sidebar.button("Login"):
        if password_input == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.sidebar.success("Logged in as admin.")
        else:
            st.sidebar.error("Incorrect password.")
else:
    st.sidebar.success("Admin logged in")
    if st.sidebar.button("Logout"):
        st.session_state.is_admin = False


# -----------------------------
# USER VIEW
# -----------------------------
def user_view():
    st.title("🗳️ Simple Voting System (Advanced)")

    data = st.session_state.data
    poll = get_active_poll(data)

    if poll is None:
        st.info("No active poll right now. Please check back later.")
        return

    poll_id = poll["id"]
    st.subheader("📌 Current Active Poll")
    st.markdown(f"**Question:** {poll['question']}")

    # Check if user already voted in this poll
    if poll_id in st.session_state.voted_polls:
        st.warning("You have already voted in this poll.")
    else:
        with st.form("vote_form"):
            if poll.get("collect_names", False):
                name = st.text_input("Your Name (optional)")
            else:
                name = ""

            choice = st.radio("Select an option:", poll["options"])
            submitted = st.form_submit_button("Submit Vote")

            if submitted:
                # Update votes
                poll["votes"][choice] += 1

                # Store voter details if enabled and name is not empty
                if poll.get("collect_names", False) and name.strip():
                    poll["voters"].append(
                        {"name": name.strip(), "choice": choice}
                    )

                # Persist data
                save_data(data)
                st.session_state.data = data

                # Mark that this user has voted in this poll
                st.session_state.voted_polls.append(poll_id)
                st.success(f"Your vote for **{choice}** has been recorded!")

    st.markdown("---")
    st.subheader("📊 Live Results")

    # Prepare data for charts
    options = list(poll["votes"].keys())
    votes = list(poll["votes"].values())
    total_votes = sum(votes)

    if total_votes == 0:
        st.info("No votes have been cast yet. Be the first to vote!")
        return

    df = pd.DataFrame({
        "Option": options,
        "Votes": votes
    })
    df["Percentage"] = df["Votes"] / total_votes * 100

    # Bar chart
    st.markdown("**Bar Chart**")
    st.bar_chart(df.set_index("Option")["Votes"])

    # Pie chart using Altair
    st.markdown("**Pie Chart**")
    pie_chart = (
        alt.Chart(df)
        .mark_arc()
        .encode(
            theta="Votes",
            color="Option",
            tooltip=["Option", "Votes", "Percentage"]
        )
    )
    st.altair_chart(pie_chart, use_container_width=True)

    # Table view
    st.markdown("**Detailed Results**")
    st.dataframe(df.set_index("Option"))

    st.markdown(f"**Total Votes:** {int(total_votes)}")


# -----------------------------
# ADMIN VIEW
# -----------------------------
def admin_view():
    st.title("🛠️ Admin Dashboard")

    if not st.session_state.is_admin:
        st.error("You must be logged in as admin to access this page.")
        return

    data = st.session_state.data

    # ------ CREATE NEW POLL ------
    st.subheader("➕ Create New Poll")

    with st.form("create_poll_form"):
        question = st.text_input("Poll Question")

        options_text = st.text_area(
            "Poll Options (one option per line)",
            placeholder="Option A\nOption B\nOption C"
        )

        collect_names = st.checkbox("Collect voter names?", value=True)
        make_active = st.checkbox("Make this poll active", value=True)

        create_submitted = st.form_submit_button("Create Poll")

        if create_submitted:
            options = [o.strip() for o in options_text.splitlines() if o.strip()]

            if not question.strip():
                st.error("Please enter a poll question.")
            elif len(options) < 2:
                st.error("Please enter at least two options.")
            else:
                new_id = get_new_poll_id(data)
                new_poll = {
                    "id": new_id,
                    "question": question.strip(),
                    "options": options,
                    "votes": {opt: 0 for opt in options},
                    "collect_names": collect_names,
                    "voters": []
                }
                data["polls"].append(new_poll)

                if make_active:
                    data["active_poll_id"] = new_id

                save_data(data)
                st.session_state.data = data
                st.success(f"Poll created successfully with ID {new_id}.")

    st.markdown("---")

    # ------ MANAGE EXISTING POLLS ------
    st.subheader("📂 Manage Existing Polls")

    if not data["polls"]:
        st.info("No polls created yet.")
        return

    poll_labels = [
        f"ID {p['id']}: {p['question'][:50]}{'...' if len(p['question']) > 50 else ''}"
        for p in data["polls"]
    ]
    selected_index = st.selectbox(
        "Select a poll to manage",
        options=range(len(data["polls"])),
        format_func=lambda i: poll_labels[i]
    )

    selected_poll = data["polls"][selected_index]

    st.markdown(f"**Selected Poll ID:** {selected_poll['id']}")
    st.markdown(f"**Question:** {selected_poll['question']}")

    total_votes = sum(selected_poll["votes"].values())
    st.write(f"**Total Votes:** {total_votes}")
    st.write(f"**Collect Names:** {'Yes' if selected_poll['collect_names'] else 'No'}")

    is_active = (data.get("active_poll_id") == selected_poll["id"])
    st.write(f"**Active Poll:** {'✅ Active' if is_active else '❌ Not Active'}")

    col1, col2, col3 = st.columns(3)

    # Set active
    with col1:
        if st.button("Set as Active"):
            data["active_poll_id"] = selected_poll["id"]
            save_data(data)
            st.session_state.data = data
            st.success("This poll is now the active poll.")

    # Reset votes
    with col2:
        if st.button("Reset Votes"):
            selected_poll["votes"] = {opt: 0 for opt in selected_poll["options"]}
            selected_poll["voters"] = []
            save_data(data)
            st.session_state.data = data
            st.warning("Votes for this poll have been reset.")

    # Delete poll
    with col3:
        if st.button("Delete Poll"):
            poll_id_to_delete = selected_poll["id"]
            data["polls"] = [p for p in data["polls"] if p["id"] != poll_id_to_delete]
            if data.get("active_poll_id") == poll_id_to_delete:
                data["active_poll_id"] = None
            save_data(data)
            st.session_state.data = data
            st.error("Poll deleted. Reload the page to see changes.")

    # Show results table for selected poll
    st.markdown("---")
    st.markdown("### 📊 Poll Results (Selected Poll)")

    if total_votes == 0:
        st.info("No votes yet for this poll.")
    else:
        df = pd.DataFrame({
            "Option": list(selected_poll["votes"].keys()),
            "Votes": list(selected_poll["votes"].values())
        })
        df["Percentage"] = df["Votes"] / total_votes * 100

        st.dataframe(df.set_index("Option"))

        # Optional: list of voters if names collected
        if selected_poll.get("collect_names", False) and selected_poll["voters"]:
            st.markdown("#### 🧑‍🤝‍🧑 Voters List")
            voters_df = pd.DataFrame(selected_poll["voters"])
            st.dataframe(voters_df)


# -----------------------------
# MAIN ROUTER
# -----------------------------
if mode == "User Voting":
    user_view()
else:
    admin_view()
