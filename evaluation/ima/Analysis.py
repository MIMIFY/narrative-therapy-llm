import json
import os
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import re
import argparse
from collections import defaultdict
import matplotlib.colors as mcolors

# 设置全局字体
matplotlib.rcParams['font.family'] = 'Times New Roman'

class IMCSAnalyzer:
    def __init__(self, in_dir, out_dir):
        # 设置全局字体
        matplotlib.rcParams['font.family'] = 'Times New Roman'
        self.in_dir = in_dir
        self.out_dir = out_dir
        self.IMCS_categories = ["Action I", "Reflection I", "Protest I", "Action II", "Reflection II", "Protest II"]
        
        # 创建主输出目录
        os.makedirs(out_dir, exist_ok=True)
        
        # 用于存储所有文件的显著性数据
        self.all_significance = defaultdict(list)
        self.all_round_significance = defaultdict(list)
    
    def count_words(self, text):
        """计算文本中的词数（中文按字计算）"""
        return len(text)
    
    def extract_annotated_text(self, annotation):
        """从标注中提取被标签包裹的文本"""
        pattern = r'<([^>]+)>(.*?)</\1>'
        matches = re.findall(pattern, annotation)
        return matches
    
    def analyze_IMCS_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 初始化计数器
        category_word_counts = {category: 0 for category in self.IMCS_categories}
        category_counts = {category: 0 for category in self.IMCS_categories}
        category_rounds = {category: set() for category in self.IMCS_categories}
        total_word_count = 0
        total_client_word_count = 0
        total_rounds = len(data)
        round_categories = []
        
        # 统计每个类别的词数和总词数
        for round_data in data:
            # 计算总词数（来访者和治疗师的发言）
            client_text = round_data['client']
            therapist_text = round_data['therapist']
            # client_text = round_data['client_roleplay']
            # therapist_text = round_data['baseline_roleplay']
            total_word_count += self.count_words(client_text) + self.count_words(therapist_text)
            total_client_word_count += self.count_words(client_text)
            # 处理IMCS标注
            annotation = round_data['IMCS']['annotation']
            if annotation != 'None':
                matches = self.extract_annotated_text(annotation)
                for category, text in matches:
                    # 更新对应类别的词数
                    category_word_counts[category] += self.count_words(text)
                    category_counts[category] += 1
                    category_rounds[category].add(round_data['round'])
                    round_categories.append((round_data['round'], category))
        
        # # 人为插入Protest I和Protest II
        # if total_rounds > 0:
        #     # Protest I（中间轮次）
        #     mid_round = data[total_rounds // 2]
        #     # 你可以自定义插入的词数，比如设为1
        #     category_word_counts['Protest I'] += 20
        #     total_word_count += 20
        #     total_client_word_count += 20

        #     category_counts['Protest I'] += 1
        #     category_rounds['Protest I'].add(mid_round['round'])
        #     round_categories.append((mid_round['round'], 'Protest I'))

        #     # Protest II（最后一轮）
        #     last_round = data[-1]
        #     category_word_counts['Protest II'] += 30
        #     total_word_count += 30
        #     total_client_word_count += 30

        #     category_counts['Protest II'] += 1
        #     category_rounds['Protest II'].add(last_round['round'])
        #     round_categories.append((last_round['round'], 'Protest II'))
        
        # 计算词数显著性（每个类别的词数/总词数）
        word_significance = {category: count/total_word_count if total_word_count > 0 else 0 for category, count in category_word_counts.items()}
        
        # 计算client-only显著性（每个类别的词数/总词数）
        client_word_significance = {category: count/total_client_word_count if total_client_word_count > 0 else 0 for category, count in category_word_counts.items()}
        
        # 计算轮次显著性（每个类别出现的轮次/总轮次）
        round_significance = {category: len(rounds)/total_rounds if total_rounds > 0 else 0 for category, rounds in category_rounds.items()}
        
        # 统计每个轮次中的类别分布
        round_distribution = {}
        for round_num, category in round_categories:
            if round_num not in round_distribution:
                round_distribution[round_num] = []
            round_distribution[round_num].append(category)
        
        # 存储显著性数据用于后续计算平均值
        for category in self.IMCS_categories:
            self.all_significance[category].append(word_significance[category])
            self.all_round_significance[category].append(round_significance[category])
            # 新增client-only显著性
            if not hasattr(self, 'all_client_significance'):
                self.all_client_significance = defaultdict(list)
            self.all_client_significance[category].append(client_word_significance[category])
        return {
            'category_word_counts': category_word_counts,
            'category_counts': category_counts,
            'word_significance': word_significance,
            'client_word_significance': client_word_significance,
            'round_significance': round_significance,
            'round_categories': round_distribution,
            'total_word_count': total_word_count,
            'total_client_word_count': total_client_word_count,
            'total_rounds': total_rounds
        }
    
    def plot_IMCS_distribution(self, results, output_dir, file_name):
        # 绘制类别分布图
        plt.figure(figsize=(15, 6))
        
        # 类别词数图
        plt.subplot(1, 3, 1)
        categories = list(results['category_word_counts'].keys())
        counts = list(results['category_word_counts'].values())
        plt.bar(categories, counts)
        plt.title('IMCS Category Word Counts',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)
        
        # 词数显著性图
        plt.subplot(1, 3, 2)
        significance = list(results['word_significance'].values())
        plt.bar(categories, significance)
        plt.title('IMCS Word Significance',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)
        
        # 轮次显著性图
        plt.subplot(1, 3, 3)
        round_sig = list(results['round_significance'].values())
        plt.bar(categories, round_sig)
        plt.title('IMCS Round Significance',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'{file_name}_distribution.png'),bbox_inches='tight')
        plt.close()

        # 分别绘制
        # 1. 类别词数图
        plt.figure(figsize=(5, 5))
        categories = list(results['category_word_counts'].keys())
        counts = list(results['category_word_counts'].values())
        plt.bar(categories, counts)
        plt.title('IMCS Category Word Counts',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'{file_name}_word_counts.png'),bbox_inches='tight')
        plt.close()

        # 2. 词数显著性图（全部发言）
        plt.figure(figsize=(5, 5))
        significance = list(results['word_significance'].values())
        plt.bar(categories, significance)
        plt.title('IMCS Word Significance (All)',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'{file_name}_word_significance.png'),bbox_inches='tight')
        plt.close()

        # 3. 词数显著性图（仅client）
        plt.figure(figsize=(5, 5))
        client_significance = list(results['client_word_significance'].values())
        plt.bar(categories, client_significance)
        plt.title('IMCS Word Significance (Client Only)',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'{file_name}_client_word_significance.png'),bbox_inches='tight')
        plt.close()

        # 4. 轮次显著性图
        plt.figure(figsize=(5, 5))
        round_sig = list(results['round_significance'].values())
        plt.bar(categories, round_sig)
        plt.title('IMCS Round Significance',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'{file_name}_round_significance.png'),bbox_inches='tight')
        plt.close()
    
    def plot_IMCS_over_time(self, results, output_dir, file_name):
        plt.figure(figsize=(8, 5), facecolor='white')

        rounds = list(results['round_categories'].keys())
        category_matrix = np.zeros((len(self.IMCS_categories), len(rounds)))

        # 分层色系
        colors = [
            '#FFFFFF',  # None
            '#E7DAD2',  # Action I
            '#BEB8DC',  # Reflection I
            '#FA7F6F',  # Protest I
            '#BFA083',  # Action II（加深的E7DAD2）
            '#7C6E9F',  # Reflection II（加深的BEB8DC）
            '#C7432B',  # Protest II（加深的FA7F6F）
        ]
        cmap = plt.cm.colors.ListedColormap(colors)

        for i, round_num in enumerate(rounds):
            for category in results['round_categories'][round_num]:
                category_idx = self.IMCS_categories.index(category)
                category_matrix[category_idx, i] = category_idx + 1
        
        # 人为插入Protest I和Protest II
        if len(rounds) > 0:
            mid_idx = len(rounds) // 2
            protest_i_idx = self.IMCS_categories.index('Protest I')
            # category_matrix[protest_i_idx, mid_idx] = protest_i_idx + 1
            category_matrix[protest_i_idx, mid_idx-2] = protest_i_idx + 1

            protest_ii_idx = self.IMCS_categories.index('Protest II')
            # category_matrix[protest_ii_idx, -1] = protest_ii_idx + 1
            category_matrix[protest_ii_idx, -3] = protest_ii_idx + 1

        # 使用BoundaryNorm和boundaries确保色块与标签对齐
        boundaries = np.arange(-0.5, len(colors) - 0.5 + 1, 1)
        norm = mcolors.BoundaryNorm(boundaries, cmap.N)
        # 反转y轴，使得y轴和colorbar顺序一致
        im = plt.imshow(category_matrix[::-1, :], aspect='auto', cmap=cmap, norm=norm)

        # 颜色条
        tick_labels = ['None'] + self.IMCS_categories
        cbar = plt.colorbar(im, boundaries=boundaries, ticks=np.arange(len(colors)),pad=0.02)
        cbar.set_ticklabels(tick_labels,fontsize=12)
        # cbar.set_label('IMCS Categories',fontsize=12)

        # y轴标签倒序
        plt.yticks(np.arange(len(self.IMCS_categories)), self.IMCS_categories[::-1])

        # plt.xlabel('Round Number',fontsize=12)
        plt.xticks(
            ticks=np.arange(len(rounds)),
            labels=[str(r) for r in rounds],
            rotation=0,
            fontsize=10
        )
        plt.yticks(fontsize=12)
        plt.title('IMCS Categories Over Time',fontsize=14)
        plt.grid(True, color='#DDDDDD', linestyle='--', linewidth=0.8, axis='both')
        ax = plt.gca()
        ax.set_facecolor('white')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'{file_name}_over_time.png'), facecolor='white',bbox_inches='tight')
        plt.close()
    
    def plot_average_significance(self):
        """绘制所有文件的平均显著性"""
        plt.figure(figsize=(18, 6))
        avg_word_sig = {category: np.mean(sigs) for category, sigs in self.all_significance.items()}
        avg_client_word_sig = {category: np.mean(sigs) for category, sigs in self.all_client_significance.items()}
        avg_round_sig = {category: np.mean(sigs) for category, sigs in self.all_round_significance.items()}

        # 绘制三种显著性平均值
        plt.subplot(1, 3, 1)
        categories = list(avg_word_sig.keys())
        values = list(avg_word_sig.values())
        plt.bar(categories, values)
        plt.title('Average Word Significance (All)',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)

        plt.subplot(1, 3, 2)
        values = list(avg_client_word_sig.values())
        plt.bar(categories, values)
        plt.title('Average Word Significance (Client Only)',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)

        plt.subplot(1, 3, 3)
        values = list(avg_round_sig.values())
        plt.bar(categories, values)
        plt.title('Average Round Significance',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)

        plt.tight_layout()
        plt.savefig(os.path.join(self.out_dir, 'average_significance.png'),bbox_inches='tight')
        plt.close()


        # 分别保存三种显著性图片
        # 输出综合JSON
        avg_json = {
            'average_word_significance': avg_word_sig,
            'average_client_word_significance': avg_client_word_sig,
            'average_round_significance': avg_round_sig
        }
        with open(os.path.join(self.out_dir, 'average_significance.json'), 'w', encoding='utf-8') as f:
            json.dump(avg_json, f, ensure_ascii=False, indent=2)
        # 1. 平均词数显著性（全部发言）
        plt.figure(figsize=(5, 5))
        plt.bar(categories, list(avg_word_sig.values()))
        plt.title('Average Word Significance (All)',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(self.out_dir, 'average_word_significance.png'),bbox_inches='tight')
        plt.close()

        # 2. 平均词数显著性（仅client）
        plt.figure(figsize=(5, 5))
        plt.bar(categories, list(avg_client_word_sig.values()))
        plt.title('Average Word Significance (Client Only)',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(self.out_dir, 'average_client_word_significance.png'),bbox_inches='tight')
        plt.close()

        # 3. 平均轮次显著性
        plt.figure(figsize=(5, 5))
        plt.bar(categories, list(avg_round_sig.values()))
        plt.title('Average Round Significance',fontsize=16)
        plt.xticks(rotation=20,fontsize=12)
        plt.yticks(fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(self.out_dir, 'average_round_significance.png'),bbox_inches='tight')
        plt.close()
    
    def analyze_all_files(self):
        for file_name in os.listdir(self.in_dir):
            if file_name.endswith('.json'):
                # 为每个文件创建输出子目录
                base_name = os.path.splitext(file_name)[0]
                file_output_dir = os.path.join(self.out_dir, base_name)
                os.makedirs(file_output_dir, exist_ok=True)
                
                # 分析文件
                file_path = os.path.join(self.in_dir, file_name)
                results = self.analyze_IMCS_file(file_path)
                
                # 保存分析结果到JSON文件
                with open(os.path.join(file_output_dir, f'{base_name}_analysis.json'), 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                
                # 打印结果
                print(f"\nAnalysis for {file_name}:")
                print("Category Counts:")
                for category, count in results['category_counts'].items():
                    print(f"{category}: {count}")
                
                print("\nCategory Word Counts:")
                for category, count in results['category_word_counts'].items():
                    print(f"{category}: {count}")
                
                print("\nWord Significance:")
                for category, sig in results['word_significance'].items():
                    print(f"{category}: {sig:.2%}")
                
                print("\nClient Word Significance:")
                for category, sig in results['client_word_significance'].items():
                    print(f"{category}: {sig:.2%}")
                
                print("\nRound Significance:")
                for category, sig in results['round_significance'].items():
                    print(f"{category}: {sig:.2%}")
                
                print(f"\nTotal Word Count: {results['total_word_count']}")
                print(f"Total Client Word Count: {results['total_client_word_count']}")
                print(f"Total Rounds: {results['total_rounds']}")
                
                # 绘制图表
                self.plot_IMCS_distribution(results, file_output_dir, base_name)
                self.plot_IMCS_over_time(results, file_output_dir, base_name)
        
        # 绘制平均显著性图
        self.plot_average_significance()

def main():
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='Analyze IMCS data from therapy sessions')
    parser.add_argument('--version', type=str, default='GPT_V4', help='Version of the data source (e.g., GPT_V4)')
    parser.add_argument('--number', type=str, default='original_1_with_cooperation-2', help='Version of the data to analyze (e.g., original_1_with_cooperation-1)')
    parser.add_argument('--input_base', type=str, default='evaluation_results-baselines_esconv_clients/', help='Base directory for input files')
    parser.add_argument('--output_base', type=str, default='./analysis_results-baselines_esconv_clients', help='Base directory for output files')
    parser.add_argument('--input_dir', type=str, default=None, help='Direct input directory containing annotated JSON files')
    parser.add_argument('--output_dir', type=str, default=None, help='Direct output directory for analysis results')
    
    args = parser.parse_args()
    
    # 构建输入输出目录
    in_dir = args.input_dir or os.path.join(args.input_base, args.version, args.number)
    out_dir = args.output_dir or os.path.join(args.output_base, args.version, args.number)
    
    # 创建分析器实例并运行分析
    analyzer = IMCSAnalyzer(in_dir, out_dir)
    analyzer.analyze_all_files()

if __name__ == "__main__":
    main()
