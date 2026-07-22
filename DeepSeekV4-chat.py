# app.py
import streamlit as st
import requests
import json
import time
from datetime import datetime
import hashlib
import re

# 页面配置
st.set_page_config(
    page_title="DeepSeek V4 智能助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS美化界面
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #4A90D9;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #4A90D9;
        margin-bottom: 2rem;
    }
    .chat-message-user {
        background-color: #E8F4FD;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 0;
        max-width: 85%;
        float: right;
        clear: both;
    }
    .chat-message-assistant {
        background-color: #F0F0F0;
        padding: 12px 16px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        max-width: 85%;
        float: left;
        clear: both;
    }
    .chat-message-thinking {
        background-color: #FFF8E1;
        padding: 12px 16px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        max-width: 85%;
        float: left;
        clear: both;
        border-left: 4px solid #FFB300;
    }
    .timestamp {
        font-size: 0.7rem;
        color: #888;
        margin-top: 4px;
    }
    .sidebar-header {
        font-size: 1.2rem;
        font-weight: 600;
        color: #4A90D9;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .status-online {
        background-color: #4CAF50;
        color: white;
    }
    .status-offline {
        background-color: #f44336;
        color: white;
    }
    .status-thinking {
        background-color: #FFB300;
        color: white;
    }
    .stTextInput > div > div > input {
        border-radius: 20px;
    }
    .stButton > button {
        border-radius: 20px;
        background-color: #4A90D9;
        color: white;
        font-weight: 500;
        padding: 0.5rem 1.5rem;
        border: none;
    }
    .stButton > button:hover {
        background-color: #357ABD;
        color: white;
    }
    .conversation-item {
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .conversation-item:hover {
        background-color: #E8F4FD;
    }
    .conversation-item-active {
        background-color: #4A90D9;
        color: white;
    }
    .search-result {
        background-color: #F5F5F5;
        padding: 8px 12px;
        border-radius: 8px;
        margin: 4px 0;
        font-size: 0.9rem;
    }
    .thinking-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border: 2px solid #4A90D9;
        border-radius: 50%;
        border-top-color: transparent;
        animation: spin 0.8s linear infinite;
        margin-right: 8px;
    }
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
</style>
""", unsafe_allow_html=True)

# 初始化会话状态
def init_session_state():
    if "conversations" not in st.session_state:
        st.session_state.conversations = {}
    if "current_conversation" not in st.session_state:
        st.session_state.current_conversation = None
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
    if "api_base" not in st.session_state:
        st.session_state.api_base = "https://api.deepseek.com/v1"
    if "model" not in st.session_state:
        st.session_state.model = "deepseek-chat"
    if "temperature" not in st.session_state:
        st.session_state.temperature = 0.7
    if "max_tokens" not in st.session_state:
        st.session_state.max_tokens = 4096
    if "enable_search" not in st.session_state:
        st.session_state.enable_search = False
    if "enable_deep_think" not in st.session_state:
        st.session_state.enable_deep_think = False
    if "search_results" not in st.session_state:
        st.session_state.search_results = []
    if "thinking_content" not in st.session_state:
        st.session_state.thinking_content = ""
    if "is_thinking" not in st.session_state:
        st.session_state.is_thinking = False

init_session_state()

# 工具函数
def generate_conversation_id():
    return hashlib.md5(str(time.time()).encode()).hexdigest()[:8]

def create_new_conversation(title="新对话"):
    conv_id = generate_conversation_id()
    st.session_state.conversations[conv_id] = {
        "id": conv_id,
        "title": title,
        "messages": [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.session_state.current_conversation = conv_id
    return conv_id

def get_current_messages():
    if st.session_state.current_conversation and st.session_state.current_conversation in st.session_state.conversations:
        return st.session_state.conversations[st.session_state.current_conversation]["messages"]
    return []

def add_message(role, content, thinking=None, search_results=None):
    if st.session_state.current_conversation in st.session_state.conversations:
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        if thinking:
            msg["thinking"] = thinking
        if search_results:
            msg["search_results"] = search_results
        st.session_state.conversations[st.session_state.current_conversation]["messages"].append(msg)
        st.session_state.conversations[st.session_state.current_conversation]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# API调用函数
def call_deepseek_api(messages, temperature=None, max_tokens=None, enable_search=False, enable_deep_think=False):
    if not st.session_state.api_key:
        st.error("请先设置API Key")
        return None
    
    headers = {
        "Authorization": f"Bearer {st.session_state.api_key}",
        "Content-Type": "application/json"
    }
    
    # 构建请求参数
    payload = {
        "model": st.session_state.model,
        "messages": messages,
        "temperature": temperature or st.session_state.temperature,
        "max_tokens": max_tokens or st.session_state.max_tokens,
        "stream": False
    }
    
    # 添加深度思考功能（通过system prompt实现）
    if enable_deep_think:
        system_prompt = {
            "role": "system",
            "content": "请进行深度思考，在回答前先展示你的思考过程。用【思考】和【回答】两个部分来组织你的回复。"
        }
        payload["messages"] = [system_prompt] + messages
    
    # 模拟联网搜索（实际DeepSeek API暂不支持原生搜索，这里模拟）
    if enable_search:
        search_query = messages[-1]["content"] if messages else ""
        search_results = simulate_search(search_query)
        if search_results:
            context = "\n\n【联网搜索结果】\n" + "\n".join([f"- {r}" for r in search_results])
            payload["messages"][-1]["content"] += context
            st.session_state.search_results = search_results
    
    try:
        response = requests.post(
            f"{st.session_state.api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            st.error(f"API调用失败: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.Timeout:
        st.error("请求超时，请稍后重试")
        return None
    except Exception as e:
        st.error(f"发生错误: {str(e)}")
        return None

def simulate_search(query):
    """模拟联网搜索功能"""
    if not query:
        return []
    
    # 模拟搜索结果
    mock_results = [
        f"📄 搜索结果1: 关于 '{query[:30]}...' 的相关信息",
        f"📄 搜索结果2: 最新相关动态和讨论",
        f"📄 搜索结果3: 深度分析和解读"
    ]
    return mock_results

def parse_thinking_response(response):
    """解析深度思考的响应"""
    if "【思考】" in response and "【回答】" in response:
        parts = response.split("【回答】")
        thinking_part = parts[0].replace("【思考】", "").strip()
        answer_part = parts[1].strip() if len(parts) > 1 else ""
        return thinking_part, answer_part
    return "", response

# 侧边栏
with st.sidebar:
    st.image("https://via.placeholder.com/80x80/4A90D9/FFFFFF?text=DS", width=80)
    st.markdown("<h2 style='text-align:center;'>DeepSeek V4</h2>", unsafe_allow_html=True)
    
    # API配置
    st.markdown("<div class='sidebar-header'>⚙️ API配置</div>", unsafe_allow_html=True)
    api_key = st.text_input("API Key", type="password", value=st.session_state.api_key, 
                           help="sk-cb5220420a0b4892bfbaa09452dbfaf4")
    if api_key != st.session_state.api_key:
        st.session_state.api_key = api_key
    
    api_base = st.text_input("API Base URL", value=st.session_state.api_base)
    if api_base != st.session_state.api_base:
        st.session_state.api_base = api_base
    
    model = st.selectbox("模型", ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"], 
                        index=0)
    if model != st.session_state.model:
        st.session_state.model = model
    
    # 参数设置
    st.markdown("<div class='sidebar-header'>🎛️ 参数设置</div>", unsafe_allow_html=True)
    temperature = st.slider("温度 (Temperature)", 0.0, 1.0, st.session_state.temperature, 0.1)
    if temperature != st.session_state.temperature:
        st.session_state.temperature = temperature
    
    max_tokens = st.slider("最大输出长度", 256, 8192, st.session_state.max_tokens, 256)
    if max_tokens != st.session_state.max_tokens:
        st.session_state.max_tokens = max_tokens
    
    # 功能开关
    st.markdown("<div class='sidebar-header'>🔧 功能开关</div>", unsafe_allow_html=True)
    
    enable_deep_think = st.toggle("🧠 深度思考模式", value=st.session_state.enable_deep_think,
                                  help="启用后，AI会展示思考过程")
    if enable_deep_think != st.session_state.enable_deep_think:
        st.session_state.enable_deep_think = enable_deep_think
    
    enable_search = st.toggle("🌐 联网搜索", value=st.session_state.enable_search,
                             help="启用后，AI可以获取网络信息（模拟）")
    if enable_search != st.session_state.enable_search:
        st.session_state.enable_search = enable_search
    
    # 对话管理
    st.markdown("<div class='sidebar-header'>💬 对话管理</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ 新对话", use_container_width=True):
            create_new_conversation()
            st.rerun()
    with col2:
        if st.button("🗑️ 清空", use_container_width=True):
            if st.session_state.current_conversation in st.session_state.conversations:
                st.session_state.conversations[st.session_state.current_conversation]["messages"] = []
                st.rerun()
    
    # 对话列表
    st.markdown("<div class='sidebar-header'>📋 对话列表</div>", unsafe_allow_html=True)
    
    if st.session_state.conversations:
        for conv_id, conv in list(st.session_state.conversations.items())[-10:][::-1]:
            is_active = conv_id == st.session_state.current_conversation
            title = conv["title"][:20] + "..." if len(conv["title"]) > 20 else conv["title"]
            msg_count = len(conv["messages"])
            time_str = conv["updated_at"][11:16] if "updated_at" in conv else ""
            
            if st.button(
                f"{title} ({msg_count}) {time_str}",
                key=f"conv_{conv_id}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.current_conversation = conv_id
                st.rerun()
    else:
        st.info("暂无对话，点击「新对话」开始")
    
    # 状态显示
    st.markdown("<div class='sidebar-header'>📊 状态</div>", unsafe_allow_html=True)
    status_col1, status_col2 = st.columns(2)
    with status_col1:
        if st.session_state.api_key:
            st.markdown("<span class='status-badge status-online'>✅ API已连接</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='status-badge status-offline'>❌ 未配置Key</span>", unsafe_allow_html=True)
    with status_col2:
        if st.session_state.enable_deep_think:
            st.markdown("<span class='status-badge status-thinking'>🧠 思考中</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='status-badge status-online'>💬 对话模式</span>", unsafe_allow_html=True)

# 主界面
st.markdown("<div class='main-header'>🤖 DeepSeek V4 智能助手</div>", unsafe_allow_html=True)

# 检查是否有当前对话
if not st.session_state.current_conversation or st.session_state.current_conversation not in st.session_state.conversations:
    create_new_conversation()

# 显示当前对话信息
current_conv = st.session_state.conversations.get(st.session_state.current_conversation, {})
messages = current_conv.get("messages", [])

# 显示消息
st.markdown("### 💬 对话区域")

# 消息显示容器
message_container = st.container()

with message_container:
    if not messages:
        st.info("👋 开始新的对话吧！")
    else:
        for idx, msg in enumerate(messages):
            role = msg.get("role", "")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            thinking = msg.get("thinking", "")
            search_results = msg.get("search_results", [])
            
            if role == "user":
                st.markdown(f"""
                <div class='chat-message-user'>
                    <strong>👤 你</strong>
                    <div>{content}</div>
                    <div class='timestamp'>{timestamp}</div>
                </div>
                """, unsafe_allow_html=True)
            elif role == "assistant":
                # 如果有思考内容，显示思考部分
                if thinking:
                    st.markdown(f"""
                    <div class='chat-message-thinking'>
                        <strong>🧠 思考过程</strong>
                        <div>{thinking}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 显示回答
                st.markdown(f"""
                <div class='chat-message-assistant'>
                    <strong>🤖 DeepSeek</strong>
                    <div>{content}</div>
                    <div class='timestamp'>{timestamp}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 显示搜索结果
                if search_results:
                    with st.expander("🌐 查看联网搜索结果"):
                        for result in search_results:
                            st.markdown(f"<div class='search-result'>{result}</div>", unsafe_allow_html=True)

# 输入区域
st.markdown("---")
input_col, button_col = st.columns([6, 1])

with input_col:
    user_input = st.chat_input("输入你的问题...", key="user_input")

with button_col:
    # 清空输入按钮占位
    pass

# 处理用户输入
if user_input:
    # 添加用户消息
    add_message("user", user_input)
    
    # 获取对话历史
    conv_history = get_current_messages()
    messages_for_api = [{"role": m["role"], "content": m["content"]} for m in conv_history]
    
    # 显示思考状态
    with st.spinner("DeepSeek正在思考..."):
        # 调用API
        response = call_deepseek_api(
            messages_for_api,
            enable_search=st.session_state.enable_search,
            enable_deep_think=st.session_state.enable_deep_think
        )
        
        if response:
            thinking_part = ""
            answer_part = response
            
            # 解析深度思考响应
            if st.session_state.enable_deep_think:
                thinking_part, answer_part = parse_thinking_response(response)
            
            # 获取搜索结果
            search_results = st.session_state.search_results if st.session_state.enable_search else []
            st.session_state.search_results = []
            
            # 添加AI回复
            add_message("assistant", answer_part, thinking=thinking_part, search_results=search_results)
            
            # 更新对话标题
            if len(messages) <= 2:  # 第一条消息
                title = user_input[:30] + "..." if len(user_input) > 30 else user_input
                st.session_state.conversations[st.session_state.current_conversation]["title"] = title
    
    st.rerun()

# 底部信息
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"📊 对话数: {len(st.session_state.conversations)}")
with col2:
    st.caption(f"💬 消息数: {len(messages)}")
with col3:
    st.caption(f"🔄 更新: {current_conv.get('updated_at', '')}")

# 快捷键提示
st.markdown("""
<small>
💡 快捷键: Enter发送 | Shift+Enter换行
</small>
""", unsafe_allow_html=True)