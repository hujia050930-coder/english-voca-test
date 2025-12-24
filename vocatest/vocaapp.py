#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
英语词汇量自适应测试系统 - 修复版
"""

# ==================== 第一部分：必需导入和配置 ====================
import streamlit as st

# 页面配置（必须是第一个Streamlit命令）
st.set_page_config(
    page_title="英语词汇量自适应测试",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 第二部分：其他导入 ====================
import pandas as pd
import random
import os
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import hashlib
import time
import json
from collections import defaultdict
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# ==================== 第三部分：常量配置 ====================
# 难度等级配置
DIFFICULTY_LEVELS = {
    1: {
        "name": "小学初中词汇", 
        "base_score": 1, 
        "increment": 1800, 
        "color": "#87CEEB",
        "description": "基础日常词汇，适合初学者"
    },
    2: {
        "name": "高中词汇", 
        "base_score": 2, 
        "increment": 1700, 
        "color": "#6495ED",
        "description": "中等难度词汇，适合高中水平"
    },
    3: {
        "name": "四六级词汇", 
        "base_score": 3, 
        "increment": 2500, 
        "color": "#4169E1",
        "description": "大学英语考试核心词汇"
    },
    4: {
        "name": "专四雅思托福", 
        "base_score": 4, 
        "increment": 4000, 
        "color": "#191970",
        "description": "专业考试和留学常用词汇"
    },
    5: {
        "name": "GRE专八词汇", 
        "base_score": 5, 
        "increment": 5000, 
        "color": "#000080",
        "description": "高级学术和研究生水平词汇"
    }
}

# 系统配置
BASE_VOCABULARY = 500      # 基础词汇量
MAX_QUESTIONS = 25         # 最大题目数
INITIAL_DIFFICULTY = 3     # 起始难度
QUESTION_BANK_FILE = "vocatest/data.xlsx"  # 题库文件名
RESULTS_FILE = "vocabulary_test_results.csv"  # 结果保存文件

# ==================== 第四部分：核心函数 - 数据加载 ====================
@st.cache_data
def load_question_bank():
    """
    加载词汇题库
    返回：题目列表，如果失败返回空列表
    """
    import os
    st.write("🔍 正在检查文件...")
    st.write(f"当前目录: {os.getcwd()}")
    st.write(f"文件列表: {os.listdir('.')}")
    # 检查文件是否存在
    file_path = "vocatest/data.xlsx" if os.path.exists("vocatest") else "data.xlsx"
    
    if not os.path.exists(file_path):
        st.write(f"❌ 找不到文件: {file_path}")
        # 列出所有可能的文件
        all_files = []
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.xlsx'):
                    all_files.append(os.path.join(root, file))
        st.write(f"找到的所有Excel文件: {all_files}")
        return []
    
    st.write(f"✅ 找到文件: {file_path}")

        
    if not os.path.exists(QUESTION_BANK_FILE):
        return []
    
    try:
        all_questions = []
        sheet_names = ["小学初中", "高中", "四六级", "专四雅思托福", "GRE专八"]
        
        for difficulty_level, sheet_name in enumerate(sheet_names, 1):
            try:
                # 读取Excel表格
                df = pd.read_excel(QUESTION_BANK_FILE, sheet_name=sheet_name)
                
                # 检查必要的列
                required_columns = ['question', 'correct_option', 'option_a', 'option_b']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    continue
                
                # 处理每一行数据
                for idx, row in df.iterrows():
                    try:
                        # 确保题目不为空
                        question_text = str(row['question']).strip()
                        if not question_text:
                            continue
                        
                        # 转换正确答案
                        correct_option = str(row['correct_option']).strip().upper()
                        option_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                        correct_index = option_map.get(correct_option, 0)
                        
                        # 收集选项
                        options = []
                        option_keys = ['option_a', 'option_b', 'option_c', 'option_d']
                        
                        for opt_key in option_keys:
                            if opt_key in row and not pd.isna(row[opt_key]):
                                options.append(str(row[opt_key]).strip())
                            else:
                                options.append("")
                        
                        # 确保至少有2个有效选项
                        valid_options = [opt for opt in options if opt.strip()]
                        if len(valid_options) < 2:
                            continue
                        
                        # 创建题目对象
                        question = {
                            'id': f"L{difficulty_level}_{idx + 1}",
                            'question': question_text,
                            'options': options,
                            'correct': correct_index,
                            'difficulty': difficulty_level,
                            'sheet_name': sheet_name
                        }
                        
                        all_questions.append(question)
                        
                    except Exception as row_error:
                        continue
                
            except Exception as sheet_error:
                continue
        
        return all_questions
            
    except Exception as e:
        return []

# ==================== 第五部分：核心函数 - 会话状态管理 ====================
def init_session_state():
    """初始化所有会话状态变量"""
    # 用户信息
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""
    if 'test_id' not in st.session_state:
        st.session_state.test_id = ""
    
    # 测试状态
    if 'test_phase' not in st.session_state:
        st.session_state.test_phase = "welcome"  # welcome, testing, results
    
    # 题目管理
    if 'current_question_num' not in st.session_state:
        st.session_state.current_question_num = 1
    if 'current_difficulty' not in st.session_state:
        st.session_state.current_difficulty = INITIAL_DIFFICULTY
    if 'used_question_ids' not in st.session_state:
        st.session_state.used_question_ids = set()
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = []
    if 'first_two_results' not in st.session_state:
        st.session_state.first_two_results = []  # 存储前两题对错
    
    # 当前题目
    if 'current_question_data' not in st.session_state:
        st.session_state.current_question_data = None
    if 'user_selection' not in st.session_state:
        st.session_state.user_selection = None
    if 'show_feedback' not in st.session_state:
        st.session_state.show_feedback = False
    if 'feedback_message' not in st.session_state:
        st.session_state.feedback_message = ""
    
    # 结果数据
    if 'test_results' not in st.session_state:
        st.session_state.test_results = None

def reset_test_state():
    """重置测试状态，准备开始新测试"""
    st.session_state.test_phase = "testing"
    st.session_state.current_question_num = 1
    st.session_state.current_difficulty = INITIAL_DIFFICULTY
    st.session_state.used_question_ids = set()
    st.session_state.user_answers = []
    st.session_state.first_two_results = []
    st.session_state.current_question_data = None
    st.session_state.user_selection = None
    st.session_state.show_feedback = False
    st.session_state.feedback_message = ""
    st.session_state.test_results = None

# ==================== 第六部分：核心函数 - 自适应逻辑 ====================
def select_next_question(question_bank, target_difficulty):
    """
    根据目标难度选择下一道题目
    返回：题目数据 或 None（如果没有题目）
    """
    # 筛选符合条件的题目
    available_questions = [
        q for q in question_bank 
        if q['difficulty'] == target_difficulty 
        and q['id'] not in st.session_state.used_question_ids
    ]
    
    if not available_questions:
        # 如果没有目标难度的题目，选择其他未使用的题目
        available_questions = [
            q for q in question_bank 
            if q['id'] not in st.session_state.used_question_ids
        ]
    
    if not available_questions:
        return None
    
    # 随机选择一道题目
    selected_question = random.choice(available_questions)
    
    # 标记为已使用
    st.session_state.used_question_ids.add(selected_question['id'])
    
    return selected_question

def calculate_next_difficulty(is_correct):
    """
    根据答题结果计算下一题的难度
    返回：下一个难度等级 (1-5)
    """
    current_q_num = st.session_state.current_question_num
    current_diff = st.session_state.current_difficulty
    
    # 规则1：前2题固定为初始难度
    if current_q_num <= 2:
        return INITIAL_DIFFICULTY
    
    # 规则2：第3题根据前2题结果调整
    elif current_q_num == 3:
        if len(st.session_state.first_two_results) == 2:
            correct_count = sum(st.session_state.first_two_results)
            if correct_count == 2:   # 全对
                return 4
            elif correct_count == 1: # 对1错1
                return 3
            else:                    # 全错
                return 2
    
    # 规则3：第4题开始，答对升1级，答错降1级
    if is_correct:
        return min(current_diff + 1, 5)  # 最高不超过5级
    else:
        return max(current_diff - 1, 1)  # 最低不低于1级

def process_user_answer(selected_option, question_data):
    """
    处理用户答案
    返回：是否处理成功
    """
    if selected_option is None:
        return False
    
    # 获取正确答案
    correct_answer = question_data['options'][question_data['correct']]
    is_correct = (selected_option == correct_answer)
    
    # 记录答案
    answer_record = {
        'question_id': question_data['id'],
        'question_text': question_data['question'],
        'user_answer': selected_option,
        'correct_answer': correct_answer,
        'is_correct': is_correct,
        'difficulty': question_data['difficulty'],
        'question_num': st.session_state.current_question_num
    }
    
    st.session_state.user_answers.append(answer_record)
    
    # 记录前两题结果
    if st.session_state.current_question_num <= 2:
        st.session_state.first_two_results.append(is_correct)
    
    # 计算下一题难度（但不显示给用户）
    next_diff = calculate_next_difficulty(is_correct)
    st.session_state.current_difficulty = next_diff
    
    # 直接进入下一题，不显示反馈
    return True

def advance_to_next_question():
    """前进到下一题"""
    st.session_state.current_question_num += 1
    st.session_state.current_question_data = None
    st.session_state.user_selection = None
    st.session_state.show_feedback = False
    st.session_state.feedback_message = ""

# ==================== 第七部分：核心函数 - 结果计算 ====================
def calculate_test_results():
    """
    计算测试结果
    返回：包含所有结果数据的字典
    """
    user_answers = st.session_state.user_answers
    
    # 基本统计
    total_questions = len(user_answers)
    correct_count = sum(1 for ans in user_answers if ans['is_correct'])
    accuracy = (correct_count / total_questions * 100) if total_questions > 0 else 0
    
    # 按难度统计
    difficulty_stats = {}
    for diff in range(1, 6):
        diff_questions = [ans for ans in user_answers if ans['difficulty'] == diff]
        diff_total = len(diff_questions)
        diff_correct = sum(1 for ans in diff_questions if ans['is_correct'])
        
        if diff_total > 0:
            diff_accuracy = diff_correct / diff_total * 100
        else:
            diff_accuracy = 0
        
        difficulty_stats[diff] = {
            'total': diff_total,
            'correct': diff_correct,
            'accuracy': diff_accuracy,
            'mastery': diff_accuracy / 100  # 掌握度 (0-1)
        }
    
    # 计算词汇量
    vocabulary_increment = 0
    for diff in range(1, 6):
        mastery = difficulty_stats[diff]['mastery']
        increment = DIFFICULTY_LEVELS[diff]["increment"]
        vocabulary_increment += increment * mastery
    
    total_vocabulary = BASE_VOCABULARY + vocabulary_increment
    
    # 计算分数
    total_score = 0
    max_score = 0
    for ans in user_answers:
        diff = ans['difficulty']
        weight = DIFFICULTY_LEVELS[diff]["base_score"]
        max_score += weight
        if ans['is_correct']:
            total_score += weight
    
    score_percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    # 最终难度评估
    final_difficulty = st.session_state.current_difficulty
    difficulty_name = DIFFICULTY_LEVELS[final_difficulty]["name"]
    
    # 学习建议
    if total_vocabulary < 2500:
        suggestion = "建议从基础词汇开始系统学习"
    elif total_vocabulary < 5000:
        suggestion = "建议巩固四六级词汇"
    elif total_vocabulary < 8000:
        suggestion = "建议学习雅思托福词汇"
    elif total_vocabulary < 12000:
        suggestion = "建议学习GRE专业词汇"
    else:
        suggestion = "您的词汇量非常丰富，建议通过原版书籍和学术文献继续扩展"
    
    results = {
        'user_name': st.session_state.user_name,
        'test_id': st.session_state.test_id,
        'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        
        # 基本统计
        'total_questions': total_questions,
        'correct_count': correct_count,
        'accuracy': accuracy,
        
        # 分数
        'total_score': total_score,
        'max_score': max_score,
        'score_percentage': score_percentage,
        
        # 词汇量
        'base_vocabulary': BASE_VOCABULARY,
        'vocabulary_increment': vocabulary_increment,
        'total_vocabulary': total_vocabulary,
        
        # 难度分析
        'difficulty_stats': difficulty_stats,
        'final_difficulty': final_difficulty,
        'final_difficulty_name': difficulty_name,
        
        # 学习建议
        'suggestion': suggestion,
        
        # 详细记录
        'answers': user_answers
    }
    
    return results

def save_results_to_file(results):
    """保存测试结果到CSV文件"""
    try:
        # 准备要保存的数据
        save_data = {
            'test_id': results['test_id'],
            'user_name': results['user_name'],
            'test_date': results['test_date'],
            'total_questions': results['total_questions'],
            'correct_count': results['correct_count'],
            'accuracy': f"{results['accuracy']:.1f}%",
            'total_score': f"{results['total_score']}/{results['max_score']}",
            'total_vocabulary': int(results['total_vocabulary']),
            'final_difficulty': f"Lv.{results['final_difficulty']}",
            'suggestion': results['suggestion']
        }
        
        # 添加各难度掌握度
        for diff in range(1, 6):
            stats = results['difficulty_stats'][diff]
            save_data[f'level{diff}_mastery'] = f"{stats['accuracy']:.1f}%"
        
        # 保存到DataFrame
        df = pd.DataFrame([save_data])
        
        # 追加到CSV文件
        if os.path.exists(RESULTS_FILE):
            existing_df = pd.read_csv(RESULTS_FILE)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
        else:
            combined_df = df
        
        # 保存文件
        combined_df.to_csv(RESULTS_FILE, index=False, encoding='utf-8-sig')
        
        return True
    except Exception as e:
        return False

# ==================== 第八部分：UI页面函数 ====================
def show_welcome_page():
    """显示欢迎页面"""

    st.markdown('<div class="welcome-header"><h1> 英语词汇量自适应测试系统</h1></div>', unsafe_allow_html=True)
    
    # 两列布局
    col1, col2 = st.columns(2)
    
    with col1:
        
        st.markdown("### 测试规则")
        st.markdown("""
        1. 测试共 **25题**，约需5-10分钟
        2. 系统根据答题表现自动调整难度
        3. 请认真回答每一道题目
        4. 测试结束后会显示详细结果
        """)
    
    with col2:
        st.markdown("### 难度等级")
        
        for level in range(1, 6):
            info = DIFFICULTY_LEVELS[level]
            with st.expander(f"**Lv.{level}: {info['name']}**", expanded=(level<=2)):
                st.markdown(f"**难度描述:** {info['description']}")
                st.markdown(f"**词汇增量:** {info['increment']:,} 词")
                st.markdown(f"**掌握该等级可增加词汇量约 {info['increment']} 词**")
    
    # 开始测试表单
    st.markdown("---")
    st.markdown("### 开始测试")
    
    with st.form(key="start_test_form"):
        user_name = st.text_input(
            "请输入您的姓名或昵称",
            placeholder="如：张三、Alice、英语学习者",
            help="建议使用2-10个字符"
        )
        
        # 使用两列布局放置按钮
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            start_button = st.form_submit_button(
                "开始词汇量测试 →",
                type="primary",
                use_container_width=True
            )
    
    # 处理开始测试
    if start_button:
        if user_name and 2 <= len(user_name.strip()) <= 20:
            st.session_state.user_name = user_name.strip()
            
            # 生成唯一的测试ID
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            unique_hash = hashlib.md5(f"{user_name}{timestamp}".encode()).hexdigest()[:8]
            st.session_state.test_id = f"VT_{timestamp}_{unique_hash}"
            
            # 重置测试状态
            reset_test_state()
            
            # 显示成功消息并刷新
            st.success(f"测试即将开始")
            time.sleep(1)
            st.rerun()
        else:
            st.error("请输入2-20个字符的姓名或昵称")

def show_testing_page(question_bank):
    """显示测试页面"""
    current_q = st.session_state.current_question_num
    
    # 检查测试是否应该结束
    if current_q > MAX_QUESTIONS:
        st.session_state.test_phase = "results"
        st.rerun()
        return
    
    # 显示进度 - 修复进度条越界问题
    progress = min(current_q / MAX_QUESTIONS, 1.0)  # 确保不超过1.0
    
    # 简洁的进度显示
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### 第 {current_q} 题 / 共 {MAX_QUESTIONS} 题")
    with col2:
        st.markdown("### 测试中")
    
    # 进度条
    st.progress(progress)
    
    # 直接显示题目，不显示反馈
    if st.session_state.current_question_data is None:
        # 确定目标难度
        if current_q <= 2:
            target_difficulty = INITIAL_DIFFICULTY
        else:
            target_difficulty = st.session_state.current_difficulty
        
        # 选择题目
        question_data = select_next_question(question_bank, target_difficulty)
        
        if question_data is None:
            st.session_state.test_phase = "results"
            st.rerun()
            return
        
        st.session_state.current_question_data = question_data
    
    question_data = st.session_state.current_question_data
    
    # 显示题目卡片
    with st.container():
        st.markdown("---")
        
        # 题目内容
        st.markdown(f"#### {question_data['question']}")
        
        # 选项 - 使用radio
        options = question_data['options']
        
        # 如果有选项为空，过滤掉
        valid_options = [opt for opt in options if opt.strip()]
        if len(valid_options) < 2:
            # 跳过无效题目
            advance_to_next_question()
            st.rerun()
            return
        
        # 显示选项
        selected = st.radio(
            "请选择正确答案:",
            options,
            key=f"question_{current_q}",
            index=None,
            label_visibility="collapsed"
        )
        
        # 更新选择
        st.session_state.user_selection = selected
        
        # 提交按钮
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit_disabled = (selected is None)
            submit_label = "提交答案" if not submit_disabled else "请先选择答案"
            
            if st.button(
                submit_label,
                type="primary" if not submit_disabled else "secondary",
                disabled=submit_disabled,
                use_container_width=True
            ):
                # 处理答案
                if process_user_answer(selected, question_data):
                    # 直接进入下一题，不显示反馈
                    advance_to_next_question()
                    st.rerun()

def show_results_page():
    """显示结果页面"""
    # 计算结果
    if st.session_state.test_results is None:
        st.session_state.test_results = calculate_test_results()
    
    results = st.session_state.test_results
    
    # 保存结果到文件
    save_results_to_file(results)
    
    # 页面标题
    st.markdown('测试完成')
    st.markdown("---")

    # 关键指标卡片
    st.markdown("### 关键指标")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("词汇量估算", f"{int(results['total_vocabulary']):,}")
        st.caption("个单词")
    
    with col2:
        st.metric("正确率", f"{results['accuracy']:.1f}%")
        st.caption(f"{results['correct_count']}/{results['total_questions']}")
    
    with col3:
        st.metric("测试得分", f"{results['total_score']}/{results['max_score']}")
        st.caption(f"{results['score_percentage']:.1f}%")
    
    with col4:
        st.metric("最终难度", f"Lv.{results['final_difficulty']}")
        st.caption(results['final_difficulty_name'])
    

    # 各难度掌握度柱状图
    st.markdown("---")
    st.markdown("### 各难度等级掌握度")
    
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    
    difficulties = list(range(1, 6))
    mastery_levels = [results['difficulty_stats'][i]['accuracy'] for i in difficulties]
    level_names = [DIFFICULTY_LEVELS[i]["name"] for i in difficulties]
    level_colors = [DIFFICULTY_LEVELS[i]["color"] for i in difficulties]
    
    bars = ax2.bar(level_names, mastery_levels, color=level_colors, edgecolor='black', linewidth=1.5)
    
    ax2.set_ylabel('mastery degree (%)', fontsize=12)
    ax2.set_ylim(0, 105)
    ax2.set_title('VOCA mastery degree', fontsize=16, fontweight='bold', pad=20)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 在柱子上添加数值标签
    for bar, value in zip(bars, mastery_levels):
        height = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width()/2., 
            height + 1,
            f'{value:.1f}%',
            ha='center', 
            va='bottom',
            fontweight='bold',
            fontsize=11
        )
    
    st.pyplot(fig2)
    
    # 详细答题记录
    st.markdown("---")
    st.markdown("### 详细答题记录")
    
    if results['answers']:
        records_data = []
        for i, ans in enumerate(results['answers'], 1):
            diff_name = DIFFICULTY_LEVELS[ans['difficulty']]["name"]
            status = "正确" if ans['is_correct'] else "错误"
            
            records_data.append({
                "题号": i,
                "难度": f"Lv.{ans['difficulty']}",
                "难度名称": diff_name,
                "状态": status,
                "您的答案": ans['user_answer'][:30] + ("..." if len(ans['user_answer']) > 30 else ""),
                "正确答案": ans['correct_answer'][:30] + ("..." if len(ans['correct_answer']) > 30 else "")
            })
        
        df_records = pd.DataFrame(records_data)
        st.dataframe(df_records, use_container_width=True, hide_index=True)
    
    # 学习建议
    st.markdown("---")
    st.markdown("### 学习建议")
    
    with st.container():
        st.info(results['suggestion'])
        

    
    # 操作按钮
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("重新测试", use_container_width=True):
            reset_test_state()
            st.rerun()
    
    with col2:
        # 生成可下载的报告
        report_text = f"""英语词汇量测试报告
{'='*50}

测试者: {results['user_name']}
测试ID: {results['test_id']}
测试时间: {results['test_date']}

测试结果
总题数: {results['total_questions']}
答对数: {results['correct_count']}
正确率: {results['accuracy']:.1f}%

词汇量估算
总词汇量: {int(results['total_vocabulary']):,} 词
基础词汇: {BASE_VOCABULARY:,} 词
增量词汇: {results['vocabulary_increment']:.0f} 词

各等级掌握度
"""
        
        for i in range(1, 6):
            stats = results['difficulty_stats'][i]
            report_text += f"{DIFFICULTY_LEVELS[i]['name']}: {stats['accuracy']:.1f}%\n"
        
        report_text += f"""
学习建议
{results['suggestion']}

{'='*50}
感谢使用英语词汇量自适应测试系统！
"""
        
        st.download_button(
            label="下载报告",
            data=report_text,
            file_name=f"词汇量测试报告_{results['user_name']}_{results['test_id'][-8:]}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col3:
        if st.button("返回首页", use_container_width=True):
            st.session_state.test_phase = "welcome"
            st.session_state.user_name = ""
            st.rerun()

def show_sidebar():
    """显示侧边栏"""
    with st.sidebar:
        st.title("词汇测试")
        
        # 显示当前状态
        if st.session_state.user_name:
            st.info(f"**测试者:** {st.session_state.user_name}")
        
        st.markdown("---")
        
        # 只在测试中显示进度
        if st.session_state.test_phase == "testing":
            current_q = st.session_state.current_question_num
            # 修复：确保进度值在0-1之间
            progress = min(current_q / MAX_QUESTIONS, 1.0)
            
            st.markdown("### 当前进度")
            st.progress(progress)
            st.markdown(f"**第 {current_q} / {MAX_QUESTIONS} 题**")
        
        # 系统信息
        st.markdown("---")
        st.markdown("### ℹ️ 系统信息")
        st.markdown(f"**测试题数:** {MAX_QUESTIONS}")
        st.markdown(f"**基础词汇:** {BASE_VOCABULARY:,}")
        
        # 快速操作
        st.markdown("---")
        st.markdown("### 快速操作")
        
        if st.button("刷新页面", use_container_width=True):
            st.rerun()

# ==================== 第九部分：主函数 ====================
def main():
    """主程序"""
    # 初始化会话状态
    init_session_state()
    
    # 加载题库
    question_bank = load_question_bank()
    if not question_bank:
        st.error("❌ 系统无法加载题库，请检查文件后刷新页面")
        st.info(f"请确保 '{QUESTION_BANK_FILE}' 文件与程序在同一目录，且格式正确")
        if st.button(" 刷新页面"):
            st.rerun()
        return
    
    # 显示侧边栏
    show_sidebar()
    
    # 主页面逻辑
    if st.session_state.test_phase == "welcome":
        show_welcome_page()
    
    elif st.session_state.test_phase == "testing":
        show_testing_page(question_bank)
    
    elif st.session_state.test_phase == "results":
        show_results_page()

# ==================== 程序入口 ====================
if __name__ == "__main__":
    main()
