import streamlit as st

def render_rewards_tab(profile_data, save_profile_callback):
    st.subheader("🏆 Leonardo's Rewards Vault")
    st.write("Earn badges for hard work! A perfect score on a hard level or a 5-day study streak earns **1 Badge (10 mins of Diablo)**.")

    # Ensure badges key exists in profile data safely
    if "badges" not in profile_data:
        profile_data["badges"] = 0

    current_badges = profile_data["badges"]
    
    # Display current balance
    st.metric(label="🏅 Available Badges", value=current_badges)
    st.caption(f"Equivalent to: **{current_badges * 10} minutes** of Diablo time with Mum!")

    st.divider()

    st.markdown("### 🎁 Redemption Wishlist")
    
    # Define available rewards based on your badge/time scale
    rewards = [
        {"name": "10 minutes of Diablo with Mum", "cost": 1},
        {"name": "20 minutes of Diablo with Mum", "cost": 2},
        {"name": "30 minutes of Diablo with Mum (3 Badges)", "cost": 3},
    ]

    for reward in rewards:
        cols = st.columns([3, 1])
        with cols[0]:
            st.write(f"**{reward['name']}**")
            st.caption(f"Cost: {reward['cost']} Badge{'s' if reward['cost'] > 1 else ''} ({reward['cost'] * 10} mins)")
        with cols[1]:
            can_afford = current_badges >= reward['cost']
            if st.button("Redeem", key=f"redeem_{reward['name']}", disabled=not can_afford):
                profile_data["badges"] -= reward['cost']
                save_profile_callback(profile_data)
                st.success(f"Successfully redeemed: {reward['name']}! Go let Mum know! 🎉")
                st.rerun()

    st.divider()
    st.info("💡 **Parents' Note:** Redeeming a reward automatically deducts badges from his balance.")