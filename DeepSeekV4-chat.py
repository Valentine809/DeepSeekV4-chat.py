import streamlit as st
import requests
import json
import time
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 页面配置
st.set_page_config(
    page_title="DeepSeek V4 Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .chat-message.user {
        background-color: #e3f2fd;
    }
    .chat-message.assistant {
        background-color: #f5f5f5;
    }
    .chat-message .message-content {
        margin-top: 0.5rem;
    }
    .sidebar-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    .session-button {
        width: 100%;
        text-align: left;
        padding: 0.5rem 1rem;
        margin: 0.2rem 0;
        border-radius: 0.3rem;
        border: 1px solid #e0e0e0;
        background-color: white;
        cursor: pointer;
    }
    .session-button:hover {
        background-color: #f0f0f0;
    }
    .session-button.active {
        background-color: #e3f2fd;
        border-color: #2196f3;
    }
    .delete-button {
        color: red;
        background: none;
        border: none;
        cursor: pointer;
        float: right;
    }
</style>
""", unsafe_allow_html=True)

# 初始化会话状态
def init_session_state():
    """初始化会话状态"""
    if "sessions" not in st.session_state:
        st.session_state.sessions = {}
    
    if "current_session_id" not in st.session_state:
        # 创建默认会话
        session_id = str(uuid.uuid4())
        st.session_state.sessions[session_id] = {
            "name": f"对话 {len(st.session_state.sessions) + 1}",
            "messages": [],
            "created_at": datetime.now().isoformat()
        }
        st.session_state.current_session_id = session_id
    
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.getenv("DEEPSEEK_API_KEY", "")
    
    if "api_base" not in st.session_state:
        st.session_state.api_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")

def get_current_session():
    """获取当前会话"""
    return st.session_state.sessions.get(st.session_state.current_session_id)

def get_current_messages():
    """获取当前会话的消息列表"""
    session = get_current_session()
    return session["messages"] if session else []

def add_message(role, content):
    """添加消息到当前会话"""
    session = get_current_session()
    if session:
        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

def create_new_session():
    """创建新会话"""
    session_id = str(uuid.uuid4())
    st.session_state.sessions[session_id] = {
        "name": f"对话 {len(st.session_state.sessions) + 1}",
        "messages": [],
        "created_at": datetime.now().isoformat()
    }
    st.session_state.current_session_id = session_id
    return session_id

def delete_session(session_id):
    """删除会话"""
    if session_id in st.session_state.sessions:
        del st.session_state.sessions[session_id]
        # 如果删除的是当前会话，切换到第一个可用会话
        if session_id == st.session_state.current_session_id:
            if st.session_state.sessions:
                st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]
            else:
                # 如果没有会话了，创建一个新的
                create_new_session()

def rename_session(session_id, new_name):
    """重命名会话"""
    if session_id in st.session_state.sessions:
        st.session_state.sessions[session_id]["name"] = new_name

def call_deepseek_api(messages, api_key, api_base, model="deepseek-chat", temperature=0.7, max_tokens=2000):
    """调用DeepSeek API"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    
    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API调用失败: {str(e)}")
        return None

# 侧边栏 - 会话管理
def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown('<div class="sidebar-header">', unsafe_allow_html=True)
        st.title("💬 DeepSeek V4")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # API配置
        with st.expander("⚙️ API配置", expanded=False):
            api_key = st.text_input(
                "API Key",
                value=st.session_state.api_key,
                type="password",
                placeholder="输入你的DeepSeek API Key"
            )
            if api_key != st.session_state.api_key:
                st.session_state.api_key = api_key
            
            api_base = st.text_input(
                "API Base URL",
                value=st.session_state.api_base,
                placeholder="https://api.deepseek.com/v1"
            )
            if api_base != st.session_state.api_base:
                st.session_state.api_base = api_base
            
            # 模型参数
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=2.0,
                value=0.7,
                step=0.1,
                help="控制输出的随机性"
            )
            st.session_state.temperature = temperature
            
            max_tokens = st.number_input(
                "Max Tokens",
                min_value=100,
                max_value=4096,
                value=2000,
                step=100,
                help="最大生成长度"
            )
            st.session_state.max_tokens = max_tokens
        
        # 新建会话按钮
        if st.button("📝 新建对话", use_container_width=True):
            create_new_session()
            st.rerun()
        
        st.divider()
        
        # 会话列表
        st.subheader("📚 对话历史")
        
        if st.session_state.sessions:
            # 按创建时间排序
            sorted_sessions = sorted(
                st.session_state.sessions.items(),
                key=lambda x: x[1]["created_at"],
                reverse=True
            )
            
            for session_id, session_data in sorted_sessions:
                col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
                
                with col1:
                    # 会话名称（可编辑）
                    is_active = session_id == st.session_state.current_session_id
                    if is_active:
                        st.markdown(f"**{session_data['name']}**")
                    else:
                        if st.button(
                            session_data['name'],
                            key=f"session_{session_id}",
                            use_container_width=True,
                            type="secondary" if not is_active else "primary"
                        ):
                            st.session_state.current_session_id = session_id
                            st.rerun()
                
                with col2:
                    # 重命名按钮
                    if st.button("✏️", key=f"rename_{session_id}", help="重命名"):
                        new_name = st.text_input("新名称", value=session_data['name'], key=f"rename_input_{session_id}")
                        if new_name:
                            rename_session(session_id, new_name)
                            st.rerun()
                
                with col3:
                    # 删除按钮
                    if st.button("🗑️", key=f"delete_{session_id}", help="删除对话"):
                        delete_session(session_id)
                        st.rerun()
        else:
            st.info("暂无对话，创建一个新的吧！")
        
        st.divider()
        
        # 统计信息
        total_sessions = len(st.session_state.sessions)
        current_session = get_current_session()
        total_messages = len(current_session["messages"]) if current_session else 0
        
        st.caption(f"📊 总对话: {total_sessions} | 当前消息: {total_messages}")
        
        # 清空所有对话
        if st.button("🗑️ 清空所有对话", use_container_width=True):
            if st.session_state.sessions:
                st.session_state.sessions = {}
                create_new_session()
                st.rerun()

# 主聊天界面
def render_chat():
    """渲染主聊天界面"""
    st.title("🤖 DeepSeek V4 智能助手")
    
    # 显示当前会话信息
    current_session = get_current_session()
    if current_session:
        st.caption(f"当前对话: {current_session['name']}")
    
    # 显示聊天消息
    messages = get_current_messages()
    
    # 使用容器来显示聊天历史
    chat_container = st.container()
    with chat_container:
        for message in messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                # 显示时间戳
                if "timestamp" in message:
                    timestamp = datetime.fromisoformat(message["timestamp"])
                    st.caption(f"🕐 {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 输入框
    if prompt := st.chat_input("输入你的消息..."):
        # 检查API Key
        if not st.session_state.api_key:
            st.error("请先在侧边栏配置API Key")
            return
        
        # 添加用户消息
        add_message("user", prompt)
        
        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 获取完整的对话历史（用于API调用）
        history_messages = get_current_messages()
        
        # 准备API请求的消息格式
        api_messages = []
        for msg in history_messages:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # 调用API
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = call_deepseek_api(
                    messages=api_messages,
                    api_key=st.session_state.api_key,
                    api_base=st.session_state.api_base,
                    temperature=st.session_state.get("temperature", 0.7),
                    max_tokens=st.session_state.get("max_tokens", 2000)
                )
            
            if response:
                assistant_message = response["choices"][0]["message"]["content"]
                st.markdown(assistant_message)
                
                # 添加助手消息
                add_message("assistant", assistant_message)
            else:
                st.error("获取回复失败，请检查API配置或网络连接")

# 主函数
def main():
    """主函数"""
    init_session_state()
    
    # 侧边栏
    render_sidebar()
    
    # 主区域
    render_chat()
    
    # 底部信息
    st.divider()
    st.caption("💡 提示：在侧边栏配置API Key后开始对话。支持多会话管理，每个会话独立保存对话历史。")

if __name__ == "__main__":
    main()