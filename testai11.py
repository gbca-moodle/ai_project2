# python3 -m pip install requests
# python3 -m pip install bs4
# python3 -m pip install mysql-connector-python
# python3 -m pip install openai streamlit
## streamlit run testai11.py

from openai import OpenAI
import streamlit as st
from bs4 import BeautifulSoup
import requests
import re


def get_soup(url):
    page = requests.get(url)
    if page.status_code != 200:
        return False

    soup = BeautifulSoup(page.content, "html.parser")
    page_ecoding = get_encoding(soup)
    # print(page_ecoding)
    if page_ecoding == "utf-8" or page_ecoding == "UTF-8":
        soup = BeautifulSoup(page.content.decode("utf-8", "ignore"), "html.parser")
    if page_ecoding == "gb2312":
        soup = BeautifulSoup(page.content.decode("GBK", "ignore"), "html.parser")
    return soup


def get_encoding(soup):
    if soup and soup.meta:
        encod = soup.meta.get("charset")
        if encod == None:
            encod = soup.meta.get("content-type")
            if encod == None:
                content = soup.meta.get("content")
                match = re.search("charset=(.*)", content)
                if match:
                    encod = match.group(1)
                # else:
                #     raise ValueError("unable to find encoding")
    # else:
    #     raise ValueError("unable to find encoding")
    return encod


def scrap_message(message_id):
    ## load the original URL to search for frame source
    main_url = "https://www.lifechurchmissions.com/MessagePlay.aspx?m=" + str(
        message_id
    )
    # print(url)
    soup = get_soup(main_url)
    if soup == False:
        return False

    ## Get message details, title, date, verses, youtube url, etc
    msg_type = ""
    msg_title = ""
    msg_date = ""
    msg_category = ""
    msg_bible_verses = ""
    msg_youtube = ""
    msg_video = ""
    msg_audio = ""

    msg_type = soup.find(id="ctl00_ContentPlaceHolder1_lblSermonType").get_text()
    msg_title = soup.find(id="ctl00_ContentPlaceHolder1_lblSermonTitle").get_text()
    msg_date = soup.find(id="ctl00_ContentPlaceHolder1_lblMsgDate").get_text()
    msg_category = soup.find(id="ctl00_ContentPlaceHolder1_lblMsgCategory").get_text()
    msg_bible_verses = soup.find(id="ctl00_ContentPlaceHolder1_lblVerses")
    if msg_bible_verses:
        msg_bible_verses = msg_bible_verses.get_text()

    msg_youtube = soup.find(id="ctl00_ContentPlaceHolder1_divYouTube")
    if msg_youtube:
        msg_youtube = msg_youtube["onclick"].split("'")[1]

    msg_video = soup.find(id="ctl00_ContentPlaceHolder1_divCNSelfHostedVideo")
    if msg_video:
        msg_video = msg_video["onclick"].split("'")[1].split("=")[1]

    msg_audio = soup.find(id="ctl00_ContentPlaceHolder1_divCNAudio")
    if msg_audio:
        msg_audio = msg_audio["onclick"].split("'")[1].split("=")[1]

    msg_notes = []
    msg_script = []
    notes_url = ""
    script_url = ""

    ## Get notes url link
    frame1 = soup.find(id="ctl00_ContentPlaceHolder1_iftabs1")
    if frame1:
        notes_url = frame1["src"]
        print(notes_url)
        soup1 = get_soup(notes_url)
        results = soup1.find_all("body")
        msg_notes.append(results[0].get_text().lstrip().replace("\xa0", ""))

    ## Get script url link
    frame3 = soup.find(id="ctl00_ContentPlaceHolder1_iftabs3")
    if frame3:
        script_url = frame3["src"]
        soup3 = get_soup(script_url)
        results = soup3.find_all("p", {"class": "MsoNormal"})
        # results = soup3.find_all("body")

        for i, line in enumerate(results):
            if i == 0 and line.get_text().isspace():
                continue
            msg_script.append(line.get_text().lstrip().replace("\xa0", ""))

    new_notes = "<br>".join(msg_notes)  # not needed
    new_script = "<br>".join(msg_script)  # not needed

    if new_notes:
        return {"msg_title": msg_type + " | " + msg_title, "body": new_notes}
    if new_script:
        return {"msg_title": msg_type + " | " + msg_title, "body": new_script}

    # return f"No information from {main_url}"


#########################
#########################

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["OPENAI_API_KEY"],
)

# st.write("1. Summary in a 150 words paragraph in Chinese")
# st.write("2. List the key learning points.")

if "openai_model" not in st.session_state:
    # st.session_state["openai_model"] = "gpt-3.5-turbo"
    st.session_state["openai_model"] = "deepseek/deepseek-chat:free"
    # st.session_state["openai_model"] = "google/gemini-2.5-pro-exp-03-25:free"

if "displaymessages" not in st.session_state:
    st.session_state.displaymessages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if prompt := st.chat_input("Which message? Enter the number after m="):
    st.session_state.messages = []
    st.session_state.displaymessages = []

    with st.spinner("Wait for it...", show_time=True):
        page = scrap_message(prompt)
        if page["body"]:
            print(len(page["body"]))
            st.session_state.messages = [{"role": "user", "content": page["body"]}]
            st.session_state.displaymessages.append(
                {
                    "role": "assistant",
                    "content": "Page m=" + prompt + " loaded : " + page["msg_title"],
                }
            )
        else:
            st.session_state.displaymessages.append(
                {
                    "role": "assistant",
                    "content": "Web page error. Enter another message.",
                }
            )

for message in st.session_state.displaymessages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.displaymessages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Wait for it...", show_time=True):

            stream = client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
            )
            response = st.write_stream(stream)

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.displaymessages.append({"role": "assistant", "content": response})


# list the key learning points in simplified chinese
# summarise into a concise paragraph of 250 words in simplified chinese
# convert the summary into a script for introducing this topic.
# a shorter prayer that captures the key points and seeks God’s guidance in a concise way.
# from the initial content, provide 3 questions for personal spiritual reflection. Suggest possible answers.
