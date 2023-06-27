import streamlit as st

st.set_page_config(
    page_title="Hello",
    page_icon="👋",
)

st.write("# Welcome to Space Explorer! 👋")
st.sidebar.success("Select a tool above to get started!")

st.markdown(
    """
    This app uses satellite positional data captured inside TLEs (Two Line Element Sets) from 
    Celestrak that are propagated by Skyfield API.
    
    ### Want to learn more?
    - What is a [TLE](https://en.wikipedia.org/wiki/Two-line_element_set)?
    - TLE data queried from [Celestrak](http://celestrak.org/NORAD/elements/).
    - Computations on TLE done with the help of [Skyfield API](https://rhodesmill.org/skyfield/).
    - Skyfield API uses [sgp4](https://pypi.org/project/sgp4/) library to propagate TLEs.
    - UI/UX python package: Check out [streamlit.io](https://streamlit.io).

    ### Creators
    [Prit Chovatiya](https://www.linkedin.com/in/prit-chovatiya/) | Porfolio: [https://pritc.space/](https://pritc.space/)

    Celestial Insights LLC  |  [Contact Us](pritchovatiya@celestialin.com) 📥 📥 📥 

    All rights reserved.
    """
)