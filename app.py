import streamlit as st 
import requests
from google import genai 
from google.genai import types 
from prompts import SUMMARY_REQUEST_PROMPT, SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE

GEMIMI_API_KEY = st.secrets["GEMINI_API_KEY"]

@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMIMI_API_KEY)

gemini_client = get_gemini_client()
MODEL_NAME="gemini-3.8-flash"

def add_message(role, kind, content):
    st.session_state.messages.append({
        "role": role,
        "kind": kind,
        "content": content
    })
    render_message(st.session_state.messages[-1])

def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"]=="text":
            st.markdown(message["content"])
        elif message["kind"]=="image":
            st.image(message["content"])
        else:
            st.warning(f"unknown message kind: {message['kind']}")


def ask_gemini(parts):
    try:
        return st.session_state.chat.send_message(parts).text
    except Exception as error:
        return f"Sorry, something went wrong: {error}"

def send_telegram(chat_id, name, summary):

    try:
        bot_token = st.secrets["TELEGRAM_BOT_TOKEN"]

        message = f"""🐾 PetCare AI Summary for {name}

{summary}
"""

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        response = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "text": message
            },
            timeout=10
        )

        result = response.json()

        if result.get("ok"):
            return True, "Message sent successfully"

        return False, result.get(
            "description",
            "Unknown Telegram error"
        )

    except Exception as error:
        return False, str(error)


#-------- step 1: onboarding --------



if "onboarded" not in st.session_state:
    
    st.title("Know Your Pet")
    st.caption("snap ur pet and know your pet better")


    with st.form("onboarding_form"):
        name = st.text_input("Enter Your Name ")
        telegram_chat_id = st.text_input("Enter Your Telegram Chat ID ")
        submitted=st.form_submit_button("Submit")

    if submitted:
        if not  name.strip() or not telegram_chat_id.strip():
            st.warning("please enter the details")
        else:
            st.session_state.name=name.strip()
            st.session_state.telegram_chat_id=telegram_chat_id.strip()
            #activate ai
            st.session_state.chat=gemini_client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
            st.session_state.messages=[]
            st.session_state.onboarded=True
            st.rerun()
    st.stop()

#-------- step 2: Chat interface --------

header_col, button_col = st.columns([5, 2],vertical_alignment="center")
with header_col:
    st.title("Know Your Pet")
    st.caption("snap ur pet and know your pet better")  
with button_col:
   send_disabled=len(st.session_state.messages)<1
   if st.button("send to telegram",disabled=send_disabled,
                   use_container_width=True):
       with st.spinner("sending to telegram..."):
           summary=ask_gemini([SUMMARY_REQUEST_PROMPT])
       success, info=send_telegram(st.session_state.telegram_chat_id,st.session_state.name,summary)  
       if success:
           st.success("sent to telegram successfully")
       else:
           st.error(f"failed to send to telegram: {info}")

if not st.session_state.messages:
    add_message("assistant","text",WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_message(message)

user_input = st.chat_input(
              placeholder="snap ur pet and know your pet better",
              accept_file=True,
              file_type=["png","jpg","jpeg"]) 

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text=user_input.text
    parts=[]

    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user","image",photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
    if text:
        add_message("user","text",text)
        parts.append(text)
    elif photo is not None:
        parts.append("snap ur pet and know your pet better")

    with st.spinner("thinking..."):
        answer=ask_gemini(parts)
    add_message("assistant","text",answer)

    st.rerun()