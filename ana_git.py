import os
import requests
import json
from datetime import datetime, timedelta, timezone
from collections import Counter
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import time
from github import Github  # PyGithub库
from github import Auth
from deepseek import DeepSeekAPI
from dotenv import load_dotenv

@dataclass
class RepoStats:
    """仓库统计信息"""
    name: str
    is_fork: bool
    stars: int
    forks: int
    size_kb: int
    languages: Dict[str, float]
    commit_count: int
    user_commit_ratio: float
    last_activity: datetime
    files_analyzed: int
    total_lines: int
    avg_file_size: float

@dataclass
class CodePatterns:
    """代码模式特征"""
    most_used_functions: List[Tuple[str, int]]
    common_vars: List[Tuple[str, int]]
    imports: List[Tuple[str, int]]
    comments_ratio: float
    avg_line_length: float
    complexity_patterns: Dict[str, float]
    test_files_ratio: float
    docstring_presence: float
    error_handling_patterns: List[str]

class GitHubCodeProfiler:
    def __init__(self, github_token: str, deepseek_api_key: str, username: str):
        """
        初始化分析器
        
        Args:
            github_token: GitHub个人访问令牌
            deepseek_api_key: DeepSeek API密钥
            username: 要分析的GitHub用户名
        """
        self.github_token = github_token
        self.deepseek_api_key = deepseek_api_key
        self.username = username
        
        # 初始化GitHub客户端
        auth = Auth.Token(github_token)
        self.g = Github(auth=auth)
        self.user = self.g.get_user(username)
        
        # 初始化DeepSeek客户端
        self.deepseek_client = DeepSeekAPI(api_key=deepseek_api_key)
        
        # 缓存
        self.all_repos = []
        self.repo_stats = {}
        self.code_patterns = {}
        
    def get_all_repositories(self, exclude_forks: bool = True) -> List:
        """获取用户所有公开仓库"""
        print(f"正在获取 {self.username} 的GitHub仓库...")
        
        repos = list(self.user.get_repos())
        
        if exclude_forks:
            repos = [repo for repo in repos if not repo.fork]
        
        self.all_repos = repos
        print(f"共找到 {len(repos)} 个仓库")
        return repos
    
    def analyze_repository_originality(self, repo) -> Dict:
        """分析仓库原创性"""
        print(f"分析仓库: {repo.name}")
        
        # 获取提交历史
        commits = list(repo.get_commits())[:50]  # 只取最近50个提交
        
        # 统计用户自己的提交
        user_commits = 0
        total_commits = len(commits)
        
        for commit in commits:
            if commit.author and commit.author.login == self.username:
                user_commits += 1
        
        # 分析主要语言
        languages = repo.get_languages()
        
        # 计算文件数量
        contents = repo.get_contents("")
        file_count = 0
        total_size = 0
        
        # 递归统计文件
        def count_files(contents_list):
            nonlocal file_count, total_size
            for content in contents_list:
                if content.type == "file":
                    file_count += 1
                    total_size += content.size
                elif content.type == "dir":
                    try:
                        sub_contents = repo.get_contents(content.path)
                        count_files(sub_contents)
                    except:
                        continue
        
        count_files(contents)
        
        # 计算原创性分数
        originality_score = 0.0
        if not repo.fork:
            originality_score += 0.4
        if total_commits > 0:
            commit_ratio = user_commits / total_commits
            originality_score += commit_ratio * 0.3
        if file_count > 10:  # 文件数量太少可能是练习项目
            originality_score += 0.3
        
        stats = RepoStats(
            name=repo.name,
            is_fork=repo.fork,
            stars=repo.stargazers_count,
            forks=repo.forks_count,
            size_kb=repo.size,
            languages=languages,
            commit_count=total_commits,
            user_commit_ratio=user_commits/max(total_commits, 1),
            last_activity=repo.updated_at,
            files_analyzed=file_count,
            total_lines=0,  # 稍后计算
            avg_file_size=total_size/max(file_count, 1)
        )
        
        self.repo_stats[repo.name] = stats
        return {
            "repo": repo.name,
            "originality_score": round(originality_score, 2),
            "is_fork": repo.fork,
            "user_commits": user_commits,
            "total_commits": total_commits,
            "commit_ratio": round(user_commits/max(total_commits, 1), 2),
            "languages": languages,
            "file_count": file_count
        }
    
    def extract_code_samples(self, repo, max_files: int = 20) -> List[Tuple[str, str]]:
        """提取代码样本进行分析"""
        print(f"从 {repo.name} 提取代码样本...")
        
        code_samples = []
        
        # 获取仓库内容
        try:
            contents = repo.get_contents("")
        except:
            return code_samples
        
        # 常见代码文件扩展名
        code_extensions = {
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp',
            '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
            '.html', '.css', '.scss', '.less', '.json', '.xml', '.yaml',
            '.yml', '.md', '.txt', '.sql', '.sh', '.bash'
        }
        
        def collect_code_files(contents_list, path=""):
            for content in contents_list:
                if content.type == "file":
                    file_ext = Path(content.name).suffix.lower()
                    if file_ext in code_extensions:
                        # 排除大文件
                        if content.size < 10000:  # 小于10KB
                            try:
                                file_content = content.decoded_content.decode('utf-8', errors='ignore')
                                if len(file_content) > 100:  # 只取有内容的文件
                                    code_samples.append((content.path, file_content))
                                    
                                    if len(code_samples) >= max_files:
                                        return True
                            except:
                                continue
                
                elif content.type == "dir":
                    try:
                        sub_contents = repo.get_contents(content.path)
                        if collect_code_files(sub_contents, content.path):
                            return True
                    except:
                        continue
            return False
        
        collect_code_files(contents)
        return code_samples
    
    def analyze_code_patterns(self, code_samples: List[Tuple[str, str]]) -> CodePatterns:
        """分析代码模式"""
        all_code = ""
        all_lines = []
        
        for path, code in code_samples:
            all_code += f"\n\n# File: {path}\n{code}"
            lines = code.split('\n')
            all_lines.extend(lines)
        
        # 统计基本信息
        total_lines = len(all_lines)
        comment_lines = sum(1 for line in all_lines if line.strip().startswith(('//', '#', '/*', '*/', '*')))
        comments_ratio = comment_lines / max(total_lines, 1)
        
        # 分析函数使用模式
        function_patterns = Counter()
        var_patterns = Counter()
        import_patterns = Counter()
        
        for line in all_lines:
            # 检测函数调用
            func_match = re.search(r'(\w+)\(', line)
            if func_match:
                func_name = func_match.group(1)
                if len(func_name) > 2:  # 过滤短名称
                    function_patterns[func_name] += 1
            
            # 检测变量声明
            var_match = re.search(r'(?:var|let|const|int|float|str|def|class)\s+(\w+)', line)
            if var_match:
                var_name = var_match.group(1)
                var_patterns[var_name] += 1
            
            # 检测import语句
            if 'import' in line or 'require' in line or 'include' in line:
                import_patterns[line.strip()] += 1
        
        # 检测错误处理
        error_patterns = []
        error_keywords = ['try', 'catch', 'except', 'finally', 'throw', 'raise', 'error', 'exception']
        for line in all_lines:
            if any(keyword in line.lower() for keyword in error_keywords):
                error_patterns.append(line.strip())
        
        return CodePatterns(
            most_used_functions=function_patterns.most_common(20),
            common_vars=var_patterns.most_common(20),
            imports=import_patterns.most_common(20),
            comments_ratio=round(comments_ratio, 3),
            avg_line_length=sum(len(line) for line in all_lines)/max(total_lines, 1),
            complexity_patterns={},  # 可添加更复杂的分析
            test_files_ratio=0.0,  # 可添加测试文件检测
            docstring_presence=0.0,
            error_handling_patterns=list(set(error_patterns[:10]))
        )
    
    def generate_ai_profile(self, repo_analyses: List[Dict], 
                          code_patterns: CodePatterns,
                          activity_data: Dict) -> str:
        """调用DeepSeek生成程序员侧写"""
        
        # 准备分析数据
        analysis_data = {
            "username": self.username,
            "total_repos": len(repo_analyses),
            "original_repos": sum(1 for r in repo_analyses if not r.get('is_fork', True)),
            "main_languages": self._get_main_languages(repo_analyses),
            "avg_originality_score": sum(r.get('originality_score', 0) for r in repo_analyses) / len(repo_analyses),
            "code_stats": {
                "total_files_analyzed": sum(r.get('file_count', 0) for r in repo_analyses),
                "comments_ratio": code_patterns.comments_ratio,
                "common_functions": code_patterns.most_used_functions[:10],
                "error_handling_patterns": code_patterns.error_handling_patterns,
                "avg_commit_ratio": sum(r.get('commit_ratio', 0) for r in repo_analyses) / len(repo_analyses)
            },
            "activity_data": activity_data
        }
        
        # 构建提示词
        prompt = f"""
        请分析以下程序员在GitHub上的代码数据，并生成一份详细的程序员侧写报告：

        程序员: {self.username}
        
        仓库分析:
        - 总仓库数: {analysis_data['total_repos']}
        - 原创仓库数: {analysis_data['original_repos']}
        - 主要编程语言: {', '.join(analysis_data['main_languages'][:5])}
        - 平均原创性分数: {analysis_data['avg_originality_score']:.2f}/1.0
        - 平均提交占比: {analysis_data['code_stats']['avg_commit_ratio']:.1%}
        
        代码特征:
        - 注释比例: {analysis_data['code_stats']['comments_ratio']:.1%}
        - 最常用函数: {[f[0] for f in analysis_data['code_stats']['common_functions'][:5]]}
        - 错误处理模式: {analysis_data['code_stats']['error_handling_patterns'][:3] if analysis_data['code_stats']['error_handling_patterns'] else '无显著模式'}
        
        活动数据:
        - 最近活跃: {analysis_data['activity_data'].get('last_active', '未知')}
        - 近期提交频率: {analysis_data['activity_data'].get('commit_frequency', '未知')}
        
        请基于以上信息分析：
        1. 此人的编程风格和习惯
        2. 技术栈偏好
        3. 代码质量（基于注释、错误处理等）
        4. 原创性评估（是原创开发者还是主要克隆他人项目）
        5. 可能的专业领域
        6. 对代码库的掌握程度
        7. 从注释中是否能看出此人有什么特殊癖好或兴趣
        
        请给出具体的分析依据，并用中文回答，格式清晰。
        """
        
        # 调用DeepSeek API
        try:
            response = self.deepseek_client.chat_completion(
                model="deepseek-chat",
                prompt=[
                    {"role": "system", "content": "你是一个资深的代码分析专家，擅长从代码模式中分析程序员的习惯、风格和技术偏好。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                stream = True
                # max_tokens=2000
            )
            for chunk in response:
                print(chunk,end="",flush=True)
            
            return response
            # 别加什么.choices[0].message.content唠唠叨叨七荤八素的，人DS官方挺好，挺直接
            # 返回就是一字符串儿，哪儿像那openai后边儿跟一串属性跟狗链子似的
        
        except Exception as e:
            return f"DeepSeek API调用失败: {str(e)}"
    
    def analyze_user_activity(self) -> Dict:
        """分析用户活动"""
        print(f"分析用户 {self.username} 的活动数据...")
        
        # 获取用户事件
        events = list(self.user.get_events())[:100]  # 最近100个事件
        
        # 统计活动类型
        event_types = Counter([event.type for event in events])
        
        # 分析时间分布
        # 分析时间分布 - 使用时区感知的datetime
        now = datetime.now(timezone.utc)  # 使用UTC时区
        recent_events = [e for e in events 
                        if (now - e.created_at).days < 30]
        
        return {
            "total_events": len(events),
            "event_distribution": dict(event_types.most_common(10)),
            "recent_activity_count": len(recent_events),
            "last_active": events[0].created_at.strftime("%Y-%m-%d") if events else "无活动",
            "commit_frequency": f"{len(recent_events)} 次/30天"
        }
    
    def _get_main_languages(self, repo_analyses: List[Dict]) -> List[str]:
        """提取主要编程语言"""
        language_counter = Counter()
        
        for repo in repo_analyses:
            for lang, percentage in repo.get('languages', {}).items():
                language_counter[lang] += percentage
        
        return [lang for lang, _ in language_counter.most_common(10)]
    
    def run_full_analysis(self, max_repos: int = 10) -> Dict:
        """运行完整分析"""
        print(f"开始分析 GitHub 用户: {self.username}")
        print("=" * 50)
        
        # 1. 获取仓库
        repos = self.get_all_repositories(exclude_forks=True)
        repos_to_analyze = repos[:max_repos]
        
        # 2. 分析每个仓库
        repo_analyses = []
        all_code_samples = []
        
        for i, repo in enumerate(repos_to_analyze, 1):
            print(f"\n[{i}/{len(repos_to_analyze)}] 分析仓库: {repo.name}")
            
            # 分析原创性
            repo_analysis = self.analyze_repository_originality(repo)
            repo_analyses.append(repo_analysis)
            
            # 提取代码样本
            if repo_analysis['originality_score'] > 0.3:  # 只分析原创性较高的仓库
                code_samples = self.extract_code_samples(repo, max_files=5)
                all_code_samples.extend(code_samples)
            
            # 避免API限流
            time.sleep(0.5)
        
        # 3. 分析代码模式
        if all_code_samples:
            print(f"\n分析 {len(all_code_samples)} 个代码样本...")
            code_patterns = self.analyze_code_patterns(all_code_samples)
        else:
            code_patterns = CodePatterns([], [], [], 0, 0, {}, 0, 0, [])
        
        # 4. 分析用户活动
        activity_data = self.analyze_user_activity()
        
        # 5. 生成AI侧写
        print("\n生成AI分析报告...")
        ai_profile = self.generate_ai_profile(repo_analyses, code_patterns, activity_data)
        
        # 6. 生成摘要报告
        summary = self._generate_summary(repo_analyses, code_patterns, activity_data)
        
        return {
            "username": self.username,
            "summary": summary,
            "ai_profile": ai_profile,
            "repo_analyses": repo_analyses,
            "activity_data": activity_data,
            "code_stats": {
                "samples_analyzed": len(all_code_samples),
                "comments_ratio": code_patterns.comments_ratio,
                "most_common_functions": code_patterns.most_used_functions[:5]
            }
        }
    
    def _generate_summary(self, repo_analyses, code_patterns, activity_data):
        """生成摘要报告"""
        total_repos = len(repo_analyses)
        avg_originality = sum(r.get('originality_score', 0) for r in repo_analyses) / total_repos
        
        summary = f"""
        GitHub 程序员侧写分析 - {self.username}
        {'='*50}
        
        基本统计:
        - 分析仓库数: {total_repos}
        - 平均原创性分数: {avg_originality:.2f}/1.0
        - 主要语言: {', '.join(self._get_main_languages(repo_analyses)[:3])}
        
        代码质量指标:
        - 注释比例: {code_patterns.comments_ratio:.1%}
        - 活跃度: {activity_data.get('recent_activity_count', 0)} 次/30天
        
        原创性评估:
        {"✅ 主要原创开发者" if avg_originality > 0.6 else 
         "⚠️  混合型开发者" if avg_originality > 0.3 else 
         "❌ 可能主要为克隆项目"}
        
        建议:
        {self._generate_recommendations(avg_originality, code_patterns.comments_ratio)}
        """
        return summary
    
    def _generate_recommendations(self, originality, comment_ratio):
        """生成建议"""
        recommendations = []
        
        if originality < 0.3:
            recommendations.append("项目原创性较低，建议增加个人项目或对fork项目做更多实质性贡献")
        
        if comment_ratio < 0.1:
            recommendations.append("代码注释较少，建议增加文档和注释以提高可维护性")
        
        return "\n".join(recommendations) if recommendations else "代码习惯良好，继续保持！"

def main():
    """主函数"""
    # 配置信息
    load_dotenv()
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # 从环境变量读取更好
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    USERNAME = os.getenv("TGT_USERNAME") # 要分析的GitHub用户名,注意小心和本机系统用户名关键字冲突
    
    # 创建分析器
    profiler = GitHubCodeProfiler(
        github_token=GITHUB_TOKEN,
        deepseek_api_key=DEEPSEEK_API_KEY,
        username=USERNAME
    )
    
    # 运行分析
    result = profiler.run_full_analysis(max_repos=5)  # 限制分析5个仓库
    
    # 输出结果
    print("\n" + "="*60)
    print("分析完成！")
    print("="*60)
    
    print(result["summary"])
    print("\n" + "="*60)
    print("AI详细侧写:")
    print("="*60)
    print(result["ai_profile"])
    
    # 保存结果到文件
    output_dir = "./cache"
    output_file = f"{output_dir}/github_profile_{USERNAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(output_dir, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n详细结果已保存到: {output_file}")

if __name__ == "__main__":
    main()